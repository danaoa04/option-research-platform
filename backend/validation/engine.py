"""Strategy validation and robustness analysis engine."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import combinations
from random import Random
from statistics import NormalDist
from typing import Any, cast

from backend.optimization.models import (
    BooleanParameter,
    CategoricalParameter,
    FloatRangeParameter,
    IntegerRangeParameter,
    OrderedDiscreteParameter,
    ParameterDefinition,
    ParameterSpace,
)

from .exceptions import ValidationDataError
from .models import (
    BootstrapResult,
    CandidateComparisonReport,
    CandidateValidationProfile,
    CPCVResult,
    CPCVSplit,
    DeflatedSharpeResult,
    MultipleTestingResult,
    ParameterSensitivityResult,
    ParameterSensitivitySnapshot,
    PBOFoldDiagnostic,
    PBOResult,
    PerformanceDegradationResult,
    PromotionGateResult,
    PromotionTier,
    RegimeRobustnessResult,
    RobustnessComponentResult,
    RobustnessNeighborhoodResult,
    RobustnessScoreResult,
    StressScenario,
    StressTestResult,
    TemporalStabilityResult,
    ValidationCandidateResult,
    ValidationFoldMetric,
    ValidationRecord,
    ValidationRunResult,
)


@dataclass(slots=True)
class ValidationEngine:
    risk_free_rate: float = 0.0
    min_sample_size: int = 30
    significance_level: float = 0.05
    cpcv_symbol_aware: bool = True
    cpcv_regime_aware: bool = True

    def deflated_sharpe_ratio(
        self,
        returns: Sequence[float],
        *,
        number_of_trials: int,
        sample_size: int | None = None,
        assumptions: tuple[str, ...] = (),
        warnings: tuple[str, ...] = (),
    ) -> DeflatedSharpeResult:
        values = list(returns)
        if not values:
            raise ValidationDataError("returns cannot be empty")
        n = sample_size or len(values)
        if n <= 1:
            raise ValidationDataError("sample size must be greater than 1")
        if number_of_trials <= 0:
            raise ValidationDataError("number_of_trials must be positive")

        mean_return = _mean(values)
        stdev = _stddev(values)
        skewness = _skewness(values)
        kurtosis = _kurtosis(values)
        observed_sharpe = 0.0 if stdev == 0.0 else (mean_return - self.risk_free_rate) / stdev
        sharpe_uncertainty = _sharpe_uncertainty(observed_sharpe, skewness, kurtosis, n)
        expected_max_sharpe = sharpe_uncertainty * _extreme_value_quantile(number_of_trials)
        deflated = observed_sharpe - expected_max_sharpe
        confidence = NormalDist().cdf(deflated / max(sharpe_uncertainty, 1e-12))
        validity_status = "valid"
        warning_list = list(warnings)
        if n < self.min_sample_size:
            warning_list.append("sample size below recommended minimum")
            validity_status = "sparse"
        if number_of_trials > max(1, n):
            warning_list.append("multiple testing load exceeds sample size")
        if abs(skewness) > 1.5 or kurtosis > 6.0:
            warning_list.append("non-normal return shape may distort DSR")
        if not assumptions:
            warning_list.append("assumptions were inferred from sample statistics")
        return DeflatedSharpeResult(
            observed_sharpe=observed_sharpe,
            expected_max_sharpe=expected_max_sharpe,
            deflated_sharpe=deflated,
            confidence=confidence,
            sample_size=n,
            number_of_trials=number_of_trials,
            assumptions=assumptions or _default_dsr_assumptions(),
            warnings=tuple(warning_list),
            validity_status=validity_status,
            skewness=skewness,
            kurtosis=kurtosis,
        )

    def probability_of_backtest_overfitting(
        self,
        profiles: Sequence[CandidateValidationProfile],
        *,
        rank_policy: str = "out_of_sample_expected_value",
    ) -> PBOResult:
        ordered = list(profiles)
        if not ordered:
            raise ValidationDataError("candidate profiles cannot be empty")
        fold_count = len(ordered[0].folds)
        if fold_count == 0:
            raise ValidationDataError("candidate profiles must include fold metrics")
        for profile in ordered:
            if len(profile.folds) != fold_count:
                raise ValidationDataError("all candidates must have the same fold count")

        fold_ids = tuple(item.fold_id for item in ordered[0].folds)
        diagnostics: list[PBOFoldDiagnostic] = []
        wins = 0
        oos_wins = 0
        sparse_warning = len(ordered) < self.min_sample_size
        for fold_index, fold_id in enumerate(fold_ids):
            in_sample_ranked = sorted(
                ordered,
                key=lambda profile: (
                    -_fold_metric(profile.folds[fold_index], rank_policy, in_sample=True),
                    profile.candidate_id,
                ),
            )
            out_sample_ranked = sorted(
                ordered,
                key=lambda profile: (
                    -_fold_metric(profile.folds[fold_index], rank_policy, in_sample=False),
                    profile.candidate_id,
                ),
            )
            in_sample_winner = in_sample_ranked[0]
            out_sample_winner = out_sample_ranked[0]
            wins += 1
            oos_wins += int(in_sample_winner.candidate_id == out_sample_winner.candidate_id)
            for position, profile in enumerate(in_sample_ranked, start=1):
                out_rank = next(
                    index
                    for index, item in enumerate(out_sample_ranked, start=1)
                    if item.candidate_id == profile.candidate_id
                )
                degradation = out_rank - position
                logit_value = _logit_rank(out_rank, len(ordered)) - _logit_rank(
                    position, len(ordered)
                )
                diagnostics.append(
                    PBOFoldDiagnostic(
                        fold_id=fold_id,
                        candidate_id=profile.candidate_id,
                        in_sample_rank=position,
                        out_of_sample_rank=out_rank,
                        rank_degradation=degradation,
                        logit_rank_degradation=logit_value,
                        selected_in_sample=position == 1,
                        selected_out_of_sample=out_rank == 1,
                        warnings=("sparse sample",) if sparse_warning else (),
                    )
                )

        degradation_flags = [
            item.rank_degradation > 0 for item in diagnostics if item.selected_in_sample
        ]
        probability = sum(degradation_flags) / max(1, len(degradation_flags))
        warnings = []
        if sparse_warning:
            warnings.append("candidate matrix is sparse relative to the minimum sample size")
        if probability > 0.5:
            warnings.append("backtest selections frequently degrade out of sample")
        return PBOResult(
            estimated_probability=probability,
            in_sample_winner_count=wins,
            out_of_sample_winner_count=oos_wins,
            fold_diagnostics=tuple(diagnostics),
            candidate_ids=tuple(profile.candidate_id for profile in ordered),
            fold_ids=fold_ids,
            rank_policy=rank_policy,
            warnings=tuple(warnings),
            sparse_sample_warning=sparse_warning,
        )

    def generate_cpcv_splits(
        self,
        records: Sequence[ValidationRecord],
        *,
        n_groups: int,
        n_test_groups: int,
        purge_days: int = 0,
        embargo_days: int = 0,
        symbol_aware: bool = True,
        regime_aware: bool = True,
    ) -> CPCVResult:
        if not records:
            raise ValidationDataError("records cannot be empty")
        if n_groups <= 1:
            raise ValidationDataError("n_groups must be greater than 1")
        if n_test_groups <= 0 or n_test_groups >= n_groups:
            raise ValidationDataError("n_test_groups must be between 1 and n_groups - 1")
        ordered = sorted(records, key=lambda item: (item.timestamp, item.candidate_id, item.symbol))
        groups = self._group_records(ordered, n_groups)
        splits: list[CPCVSplit] = []
        warnings: list[str] = []
        for test_group_ids in combinations(range(n_groups), n_test_groups):
            train_group_ids = tuple(
                group_id for group_id in range(n_groups) if group_id not in test_group_ids
            )
            test_records = [record for group_id in test_group_ids for record in groups[group_id]]
            train_records = [record for group_id in train_group_ids for record in groups[group_id]]
            test_start = min(record.timestamp for record in test_records)
            test_end = max(record.timestamp for record in test_records)
            purge_start = test_start - timedelta(days=purge_days) if purge_days else None
            embargo_end = test_end + timedelta(days=embargo_days) if embargo_days else None
            filtered_train, leakage_warnings = self._apply_leakage_filters(
                train_records,
                test_start=test_start,
                test_end=test_end,
                purge_start=purge_start,
                embargo_end=embargo_end,
                symbol_aware=symbol_aware,
                regime_aware=regime_aware,
            )
            if leakage_warnings:
                warnings.extend(leakage_warnings)
            split_id = self._split_id(train_group_ids, test_group_ids)
            splits.append(
                CPCVSplit(
                    split_id=split_id,
                    group_ids=tuple(range(n_groups)),
                    train_group_ids=train_group_ids,
                    test_group_ids=test_group_ids,
                    train_start=min(item.timestamp for item in filtered_train),
                    train_end=max(item.timestamp for item in filtered_train),
                    test_start=test_start,
                    test_end=test_end,
                    purge_start=purge_start,
                    embargo_end=embargo_end,
                    symbol_universe=tuple(sorted({item.symbol for item in ordered})),
                    regime_labels=tuple(sorted({item.regime for item in ordered})),
                    leakage_warnings=tuple(leakage_warnings),
                    metadata={"train_count": len(filtered_train), "test_count": len(test_records)},
                )
            )
        return CPCVResult(
            n_groups=n_groups,
            n_test_groups=n_test_groups,
            splits=tuple(splits),
            warnings=tuple(warnings),
            metadata={"purge_days": purge_days, "embargo_days": embargo_days},
        )

    def multiple_testing_corrections(
        self,
        p_values: Sequence[float],
        *,
        method: str = "holm",
        significance_level: float | None = None,
        minimum_effective_sample_size: int = 1,
    ) -> MultipleTestingResult:
        values = list(p_values)
        if not values:
            raise ValidationDataError("p_values cannot be empty")
        alpha = significance_level if significance_level is not None else self.significance_level
        method_name = method.lower()
        if method_name == "bonferroni":
            adjusted = [min(1.0, value * len(values)) for value in values]
        elif method_name == "holm":
            adjusted = _holm(values)
        elif method_name in {"bh", "benjamini-hochberg", "benjamini_hochberg"}:
            adjusted = _benjamini_hochberg(values)
            method_name = "benjamini_hochberg"
        else:
            raise ValidationDataError(f"unsupported correction method '{method}'")
        rejected = tuple(value <= alpha for value in adjusted)
        fwer = min(1.0, sum(values) / len(values))
        fdr = sum(rejected) / max(1, len(rejected))
        warnings: tuple[str, ...] = ()
        if minimum_effective_sample_size < self.min_sample_size:
            warnings = ("minimum effective sample size is below the recommended threshold",)
        return MultipleTestingResult(
            method=method_name,
            significance_level=alpha,
            raw_p_values=tuple(values),
            adjusted_p_values=tuple(adjusted),
            rejected=rejected,
            family_wise_error_rate=fwer,
            false_discovery_rate=fdr,
            minimum_effective_sample_size=minimum_effective_sample_size,
            warnings=warnings,
        )

    def bootstrap_returns(
        self,
        returns: Sequence[float],
        *,
        sample_count: int,
        block_size: int = 1,
        seed: int = 0,
        method: str = "block",
    ) -> BootstrapResult:
        values = list(returns)
        if not values:
            raise ValidationDataError("returns cannot be empty")
        if sample_count <= 0:
            raise ValidationDataError("sample_count must be positive")
        if block_size <= 0:
            raise ValidationDataError("block_size must be positive")
        rng = Random(seed)
        samples: list[list[float]] = []
        for _ in range(sample_count):
            if method == "block":
                samples.append(_block_bootstrap(values, block_size=block_size, rng=rng))
            elif method == "stationary":
                samples.append(_stationary_bootstrap(values, block_size=block_size, rng=rng))
            else:
                samples.append([values[rng.randrange(len(values))] for _ in values])
        means = [_mean(sample) for sample in samples]
        stds = [_stddev(sample) for sample in samples]
        drawdowns = [_max_drawdown(sample) for sample in samples]
        return BootstrapResult(
            method=method,
            seed=seed,
            sample_count=sample_count,
            distribution_metrics={"mean": means, "stdev": stds},
            confidence_intervals={
                "mean": _percentile_interval(means),
                "stdev": _percentile_interval(stds),
            },
            drawdown_distribution=drawdowns,
            risk_of_ruin_inputs={
                "sample_size": float(len(values)),
                "block_size": float(block_size),
            },
            warnings=(),
        )

    def compare_candidates(
        self,
        candidates: Sequence[ValidationCandidateResult],
    ) -> CandidateComparisonReport:
        rows = []
        columns = (
            "candidate_id",
            "tier",
            "overall_score",
            "deflated_sharpe",
            "pbo",
            "cpcv_stability",
            "neighborhood_stability",
            "regime_stability",
            "temporal_stability",
            "stress_resistance",
        )
        for candidate in candidates:
            rows.append(
                {
                    "candidate_id": candidate.candidate_id,
                    "tier": candidate.tier.value,
                    "overall_score": candidate.robustness_score.overall_score,
                    "deflated_sharpe": candidate.deflated_sharpe.deflated_sharpe,
                    "pbo": candidate.pbo.estimated_probability,
                    "cpcv_stability": 1.0 - candidate.pbo.estimated_probability,
                    "neighborhood_stability": candidate.neighborhood.rank_stability,
                    "regime_stability": candidate.regime_robustness.stability_across_regimes,
                    "temporal_stability": (
                        1.0 - candidate.temporal_stability.exceptional_period_dependency
                    ),
                    "stress_resistance": _mean(
                        list(candidate.stress_test.average_metrics.values())
                    ),
                }
            )
        chart_data = {
            key: [float(row[key]) for row in rows if key in row]
            for key in columns
            if key not in {"candidate_id", "tier"}
        }
        return CandidateComparisonReport(
            rows=tuple(rows),
            columns=columns,
            chart_data=chart_data,
            warnings=(),
        )

    def robustness_score(
        self,
        *,
        out_of_sample_performance: float,
        deflated_sharpe: DeflatedSharpeResult,
        pbo: PBOResult,
        cpcv: CPCVResult,
        neighborhood: RobustnessNeighborhoodResult,
        regime: RegimeRobustnessResult,
        temporal: TemporalStabilityResult,
        calibration_quality: float,
        data_quality: float,
        liquidity: float,
        execution_stress_resistance: float,
        complexity_penalty: float,
        sample_reliability: float,
        weights: dict[str, float] | None = None,
        active_policy: str = "default",
        gate_result: PromotionGateResult | None = None,
    ) -> RobustnessScoreResult:
        weight_map = weights or {
            "out_of_sample_performance": 0.20,
            "deflated_sharpe": 0.15,
            "pbo": 0.15,
            "cpcv": 0.10,
            "neighborhood": 0.10,
            "regime": 0.10,
            "temporal": 0.05,
            "calibration": 0.05,
            "data_quality": 0.05,
            "liquidity": 0.03,
            "execution_stress": 0.03,
            "complexity_penalty": 0.02,
            "sample_reliability": 0.02,
        }
        component_scores = (
            RobustnessComponentResult(
                name="out_of_sample_performance",
                score=_bounded(out_of_sample_performance),
                weight=weight_map["out_of_sample_performance"],
                rationale="raw out-of-sample return",
            ),
            RobustnessComponentResult(
                name="deflated_sharpe",
                score=_bounded(
                    deflated_sharpe.confidence * max(0.0, deflated_sharpe.deflated_sharpe + 1.0)
                ),
                weight=weight_map["deflated_sharpe"],
                rationale="deflated Sharpe and confidence",
            ),
            RobustnessComponentResult(
                name="pbo",
                score=_bounded(1.0 - pbo.estimated_probability),
                weight=weight_map["pbo"],
                rationale="lower overfitting probability is better",
            ),
            RobustnessComponentResult(
                name="cpcv",
                score=_bounded(_split_stability(cpcv)),
                weight=weight_map["cpcv"],
                rationale="fold stability from CPCV",
            ),
            RobustnessComponentResult(
                name="neighborhood",
                score=_bounded(neighborhood.rank_stability),
                weight=weight_map["neighborhood"],
                rationale="parameter neighborhood stability",
            ),
            RobustnessComponentResult(
                name="regime",
                score=_bounded(regime.stability_across_regimes),
                weight=weight_map["regime"],
                rationale="regime consistency",
            ),
            RobustnessComponentResult(
                name="temporal",
                score=_bounded(1.0 - temporal.exceptional_period_dependency),
                weight=weight_map["temporal"],
                rationale="temporal stability",
            ),
            RobustnessComponentResult(
                name="calibration",
                score=_bounded(1.0 - calibration_quality),
                weight=weight_map["calibration"],
                rationale="lower calibration error is better",
            ),
            RobustnessComponentResult(
                name="data_quality",
                score=_bounded(data_quality),
                weight=weight_map["data_quality"],
                rationale="data quality gate",
            ),
            RobustnessComponentResult(
                name="liquidity",
                score=_bounded(liquidity),
                weight=weight_map["liquidity"],
                rationale="liquidity resilience",
            ),
            RobustnessComponentResult(
                name="execution_stress",
                score=_bounded(execution_stress_resistance),
                weight=weight_map["execution_stress"],
                rationale="stress resistance",
            ),
            RobustnessComponentResult(
                name="complexity_penalty",
                score=_bounded(1.0 - complexity_penalty),
                weight=weight_map["complexity_penalty"],
                rationale="lower complexity penalty is better",
            ),
            RobustnessComponentResult(
                name="sample_reliability",
                score=_bounded(sample_reliability),
                weight=weight_map["sample_reliability"],
                rationale="sample size and fold reliability",
            ),
        )
        numerator = sum(component.score * component.weight for component in component_scores)
        denominator = sum(component.weight for component in component_scores)
        overall = numerator / denominator if denominator else 0.0
        warnings: tuple[str, ...] = ()
        failures: list[str] = []
        if pbo.estimated_probability > 0.5:
            failures.append("probability of backtest overfitting is too high")
        if deflated_sharpe.validity_status != "valid":
            warnings = deflated_sharpe.warnings
        return RobustnessScoreResult(
            overall_score=overall,
            component_scores=component_scores,
            weights=weight_map,
            active_policy=active_policy,
            confidence=_bounded(deflated_sharpe.confidence),
            warnings=warnings,
            failure_reasons=tuple(failures),
            gate_results=gate_result,
        )

    def promotion_gate(
        self,
        *,
        candidate: ValidationCandidateResult,
        minimum_oos_folds: int,
        maximum_pbo: float,
        minimum_deflated_sharpe: float,
        maximum_calibration_error: float,
        minimum_sample_size: int,
        acceptable_drawdown: float,
        acceptable_stress_degradation: float,
        acceptable_regime_coverage: float,
        acceptable_parameter_stability: float,
        no_data_quality_failures: bool,
        tier: PromotionTier = PromotionTier.PRODUCTION_CANDIDATE,
    ) -> PromotionGateResult:
        checks = {
            "minimum_oos_folds": len(candidate.cpcv.splits) >= minimum_oos_folds,
            "maximum_pbo": candidate.pbo.estimated_probability <= maximum_pbo,
            "minimum_deflated_sharpe": (
                candidate.deflated_sharpe.deflated_sharpe >= minimum_deflated_sharpe
            ),
            "maximum_calibration_error": candidate.regime_robustness.regime_failure_analysis.get(
                "calibration_error", 0.0
            )
            <= maximum_calibration_error,
            "minimum_sample_size": candidate.profile.sample_size >= minimum_sample_size,
            "acceptable_drawdown": candidate.degradation.test_metrics.get("drawdown", 0.0)
            <= acceptable_drawdown,
            "acceptable_stress_degradation": _mean(
                list(candidate.stress_test.average_metrics.values())
            )
            >= acceptable_stress_degradation,
            "acceptable_regime_coverage": candidate.regime_robustness.minimum_regime_coverage
            >= acceptable_regime_coverage,
            "acceptable_parameter_stability": candidate.neighborhood.rank_stability
            >= acceptable_parameter_stability,
            "no_data_quality_failures": no_data_quality_failures and not candidate.failures,
        }
        passed = all(checks.values())
        failure_reasons: tuple[str, ...] = tuple(name for name, ok in checks.items() if not ok)
        resolved_tier = tier if passed else PromotionTier.REJECTED
        return PromotionGateResult(
            tier=resolved_tier,
            passed=passed,
            checks=checks,
            warnings=candidate.warnings,
            failure_reasons=failure_reasons,
        )

    def analyze_parameter_sensitivity(
        self,
        *,
        baseline_parameters: dict[str, float | int | str | bool],
        parameter_space: ParameterSpace,
        evaluator: Callable[[dict[str, float | int | str | bool]], dict[str, float]],
        metric_key: str,
        perturbation: int = 1,
    ) -> ParameterSensitivityResult:
        baseline_metrics = evaluator(dict(baseline_parameters))
        snapshots: list[ParameterSensitivitySnapshot] = []
        fragile: list[str] = []
        plateau: list[str] = []
        cliff: list[str] = []
        interaction_warnings: list[str] = []
        heatmap_data: dict[str, list[float]] = {}
        for parameter in parameter_space.parameters:
            neighbor_values = _neighbor_values(
                parameter,
                baseline_parameters.get(parameter.name),
                perturbation,
            )
            sensitivities: list[float] = []
            stability_values: list[float] = []
            for value in neighbor_values:
                if value == baseline_parameters.get(parameter.name):
                    continue
                perturbed = dict(baseline_parameters)
                perturbed[parameter.name] = value
                perturbed_metrics = evaluator(perturbed)
                delta = {
                    key: perturbed_metrics.get(key, 0.0) - baseline_metrics.get(key, 0.0)
                    for key in baseline_metrics.keys() | perturbed_metrics.keys()
                }
                sensitivity = delta.get(metric_key, 0.0)
                snapshots.append(
                    ParameterSensitivitySnapshot(
                        parameter_name=parameter.name,
                        baseline_value=bool(baseline_parameters[parameter.name])
                        if isinstance(baseline_parameters[parameter.name], bool)
                        else baseline_parameters[parameter.name],
                        perturbed_value=value,
                        baseline_metrics=baseline_metrics,
                        perturbed_metrics=perturbed_metrics,
                        metric_deltas=delta,
                        local_sensitivity=sensitivity,
                        stability_penalty=abs(sensitivity),
                    )
                )
                sensitivities.append(abs(sensitivity))
                stability_values.append(1.0 - min(1.0, abs(sensitivity)))
            if sensitivities:
                heatmap_data[parameter.name] = sensitivities
                if max(sensitivities) > 1.0:
                    fragile.append(parameter.name)
                if max(sensitivities) < 0.05:
                    plateau.append(parameter.name)
                if max(sensitivities) > 2.0:
                    cliff.append(parameter.name)
                if len(set(round(value, 6) for value in stability_values)) > 1:
                    interaction_warnings.append(
                        f"parameter '{parameter.name}' shows interaction effects"
                    )
        return ParameterSensitivityResult(
            baseline_metrics=baseline_metrics,
            snapshots=tuple(snapshots),
            fragile_parameters=tuple(fragile),
            plateau_parameters=tuple(plateau),
            cliff_parameters=tuple(cliff),
            interaction_warnings=tuple(interaction_warnings),
            stability_region={
                key: tuple(
                    _neighbor_values_for_result(parameter_space, key, baseline_parameters.get(key))
                )
                for key in baseline_parameters
            },
            heatmap_data=heatmap_data,
        )

    def evaluate_neighborhoods(
        self,
        *,
        candidate_id: str,
        parameters: dict[str, float | int | str | bool],
        parameter_space: ParameterSpace,
        evaluator: Callable[[dict[str, float | int | str | bool]], dict[str, float]],
        metric_key: str,
        radius: int = 1,
    ) -> RobustnessNeighborhoodResult:
        baseline_metrics = evaluator(dict(parameters))
        neighbors = _build_neighbors(parameters, parameter_space, radius)
        neighbor_metrics: list[dict[str, float]] = []
        for neighbor in neighbors:
            if neighbor == parameters:
                continue
            neighbor_metrics.append(evaluator(neighbor))
        if not neighbor_metrics:
            raise ValidationDataError("no neighbors generated for robustness evaluation")
        metric_values = [item.get(metric_key, 0.0) for item in neighbor_metrics]
        profitable = [value for value in metric_values if value > 0.0]
        dispersion = _stddev(metric_values)
        rank_stability = 1.0 - min(
            1.0,
            dispersion / max(1.0, abs(baseline_metrics.get(metric_key, 0.0))),
        )
        return RobustnessNeighborhoodResult(
            candidate_id=candidate_id,
            baseline_metrics=baseline_metrics,
            neighbor_count=len(neighbor_metrics),
            profitable_neighbor_percentage=len(profitable) / len(neighbor_metrics),
            median_neighbor_performance=_median(metric_values),
            worst_neighbor_performance=min(metric_values),
            dispersion=dispersion,
            rank_stability=_bounded(rank_stability),
            regime_stability=_bounded(1.0 - dispersion / max(1.0, len(neighbor_metrics))),
            fold_stability=_bounded(1.0 - dispersion / max(1.0, len(neighbor_metrics))),
            objective_stability=_bounded(1.0 - min(1.0, dispersion)),
            constraint_stability=_bounded(1.0 - min(1.0, dispersion / 2.0)),
            neighbor_metrics=tuple(neighbor_metrics),
            warnings=(),
        )

    def performance_degradation(
        self,
        *,
        training_metrics: dict[str, float],
        validation_metrics: dict[str, float],
        test_metrics: dict[str, float],
        walk_forward_metrics: dict[str, float],
        cpcv_metrics: dict[str, float],
        neighboring_metrics: dict[str, float],
        regime_metrics: dict[str, float],
    ) -> PerformanceDegradationResult:
        def ratio(
            base: str,
            other: str,
            metrics_a: dict[str, float],
            metrics_b: dict[str, float],
        ) -> float:
            denominator = max(abs(metrics_a.get(base, 0.0)), 1e-12)
            return (metrics_a.get(base, 0.0) - metrics_b.get(other, 0.0)) / denominator

        degradation_ratios = {
            "return": ratio("expected_value", "expected_value", training_metrics, test_metrics),
            "sharpe": ratio("sharpe", "sharpe", training_metrics, test_metrics),
            "pop": ratio("pop", "pop", training_metrics, test_metrics),
            "expected_value": ratio(
                "expected_value",
                "expected_value",
                validation_metrics,
                test_metrics,
            ),
            "drawdown": (test_metrics.get("drawdown", 0.0) - training_metrics.get("drawdown", 0.0))
            / max(abs(training_metrics.get("drawdown", 1.0)), 1e-12),
            "calibration": (
                test_metrics.get("calibration_error", 0.0)
                - training_metrics.get("calibration_error", 0.0)
            )
            / max(abs(training_metrics.get("calibration_error", 1.0)), 1e-12),
            "liquidity": (
                training_metrics.get("liquidity", 0.0) - neighboring_metrics.get("liquidity", 0.0)
            )
            / max(abs(training_metrics.get("liquidity", 1.0)), 1e-12),
            "turnover": (test_metrics.get("turnover", 0.0) - training_metrics.get("turnover", 0.0))
            / max(abs(training_metrics.get("turnover", 1.0)), 1e-12),
            "failure_rate": (
                test_metrics.get("failure_rate", 0.0) - regime_metrics.get("failure_rate", 0.0)
            )
            / max(abs(regime_metrics.get("failure_rate", 1.0)), 1e-12),
        }
        return PerformanceDegradationResult(
            training_metrics=training_metrics,
            validation_metrics=validation_metrics,
            test_metrics=test_metrics,
            walk_forward_metrics=walk_forward_metrics,
            cpcv_metrics=cpcv_metrics,
            neighboring_metrics=neighboring_metrics,
            regime_metrics=regime_metrics,
            degradation_ratios=degradation_ratios,
            warnings=tuple(key for key, value in degradation_ratios.items() if value > 0.5),
        )

    def regime_robustness(
        self,
        regime_metrics: dict[str, dict[str, float]],
        *,
        minimum_regime_coverage: float,
    ) -> RegimeRobustnessResult:
        regimes = tuple(sorted(regime_metrics))
        coverage = len(regimes) / max(1, len(regime_metrics))
        weights = {regime: 1.0 / len(regimes) for regime in regimes} if regimes else {}
        metric_keys = sorted({key for metrics in regime_metrics.values() for key in metrics})
        weighted_metrics = {
            metric: sum(
                regime_metrics[regime].get(metric, 0.0) * weights.get(regime, 0.0)
                for regime in regimes
            )
            for metric in metric_keys
        }
        worst_metrics = {
            metric: min(metrics.get(metric, 0.0) for metrics in regime_metrics.values())
            for metric in metric_keys
        }
        failure_analysis = {
            regime: sum(1.0 for value in metrics.values() if value < 0.0) / max(1, len(metrics))
            for regime, metrics in regime_metrics.items()
        }
        concentration = 1.0 - coverage
        stability = 1.0 - concentration
        return RegimeRobustnessResult(
            regime_metrics=regime_metrics,
            regime_weights=weights,
            minimum_regime_coverage=minimum_regime_coverage,
            regime_concentration_penalty=concentration,
            worst_regime_metrics=worst_metrics,
            regime_weighted_metrics=weighted_metrics,
            stability_across_regimes=_bounded(stability),
            regime_failure_analysis=failure_analysis,
            warnings=("regime coverage is below target",)
            if coverage < minimum_regime_coverage
            else (),
        )

    def temporal_stability(self, periods: dict[str, dict[str, float]]) -> TemporalStabilityResult:
        ordered = dict(sorted(periods.items()))
        metrics = sorted({key for data in ordered.values() for key in data})
        drift_metrics = {
            metric: _trend([period.get(metric, 0.0) for period in ordered.values()])
            for metric in metrics
        }
        rank_drift = abs(drift_metrics.get("rank", 0.0))
        calibration_drift = abs(drift_metrics.get("calibration_error", 0.0))
        volatility_drift = abs(drift_metrics.get("volatility_regime", 0.0))
        exceptional_period_dependency = max(
            (abs(value) for value in drift_metrics.values()), default=0.0
        )
        return TemporalStabilityResult(
            calendar_metrics=ordered,
            drift_metrics=drift_metrics,
            parameter_drift={metric: abs(value) for metric, value in drift_metrics.items()},
            rank_drift=rank_drift,
            calibration_drift=calibration_drift,
            volatility_regime_drift=volatility_drift,
            drawdown_clustering=abs(drift_metrics.get("drawdown", 0.0)),
            exceptional_period_dependency=exceptional_period_dependency,
            warnings=(),
        )

    def stress_test(
        self,
        baseline_metrics: dict[str, float],
        scenarios: Sequence[StressScenario],
    ) -> StressTestResult:
        scenario_results: list[dict[str, float]] = []
        names: list[str] = []
        warnings: list[str] = []
        for scenario in scenarios:
            adjusted = dict(baseline_metrics)
            adjusted["expected_value"] = adjusted.get("expected_value", 0.0) - (
                scenario.spread_multiplier - 1.0
            ) * abs(adjusted.get("expected_value", 0.0))
            adjusted["sharpe"] = adjusted.get("sharpe", 0.0) - scenario.slippage_bps / 10000.0
            adjusted["drawdown"] = adjusted.get("drawdown", 0.0) + scenario.commission_bps / 10000.0
            adjusted["calibration_error"] = adjusted.get("calibration_error", 0.0) + abs(
                scenario.iv_shock
            )
            adjusted["liquidity"] = adjusted.get("liquidity", 0.0) * scenario.liquidity_multiplier
            adjusted["turnover"] = adjusted.get("turnover", 0.0) + scenario.fill_delay_bars * 0.01
            scenario_results.append(adjusted)
            names.append(scenario.name)
            if adjusted.get("expected_value", 0.0) < baseline_metrics.get("expected_value", 0.0):
                warnings.append(f"{scenario.name} degrades expected value")
        worst_case_metrics = {
            key: min(result.get(key, 0.0) for result in scenario_results)
            for key in baseline_metrics
        }
        average_metrics = {
            key: _mean([result.get(key, 0.0) for result in scenario_results])
            for key in baseline_metrics
        }
        return StressTestResult(
            scenario_results=tuple(scenario_results),
            scenario_names=tuple(names),
            worst_case_metrics=worst_case_metrics,
            average_metrics=average_metrics,
            degradation_warnings=tuple(warnings),
        )

    def compare_validation_runs(
        self,
        runs: Sequence[ValidationRunResult],
    ) -> CandidateComparisonReport:
        rows = []
        for run in runs:
            rows.append(
                {
                    "run_id": run.run_id,
                    "strategy_name": run.strategy_name,
                    "overall_score": _mean(
                        [
                            candidate.robustness_score.overall_score
                            for candidate in run.candidate_results
                        ]
                    ),
                    "pbo": _mean(
                        [candidate.pbo.estimated_probability for candidate in run.candidate_results]
                    ),
                    "deflated_sharpe": _mean(
                        [
                            candidate.deflated_sharpe.deflated_sharpe
                            for candidate in run.candidate_results
                        ]
                    ),
                    "stress_resistance": _mean(
                        [
                            _mean(list(candidate.stress_test.average_metrics.values()))
                            for candidate in run.candidate_results
                        ]
                    ),
                }
            )
        return CandidateComparisonReport(
            rows=tuple(rows),
            columns=(
                "run_id",
                "strategy_name",
                "overall_score",
                "pbo",
                "deflated_sharpe",
                "stress_resistance",
            ),
            chart_data={
                "overall_score": [cast(float, row["overall_score"]) for row in rows],
                "pbo": [cast(float, row["pbo"]) for row in rows],
                "deflated_sharpe": [cast(float, row["deflated_sharpe"]) for row in rows],
                "stress_resistance": [cast(float, row["stress_resistance"]) for row in rows],
            },
            warnings=(),
        )

    def analyze_validation_run(
        self,
        *,
        run_id: str,
        strategy_name: str,
        candidate_results: Sequence[ValidationCandidateResult],
        cpcv: CPCVResult,
        random_seed: int | None,
        software_git_commit: str,
        schema_version: str,
    ) -> ValidationRunResult:
        comparison = self.compare_candidates(candidate_results)
        candidate_ordering = tuple(
            item.candidate_id
            for item in sorted(
                candidate_results,
                key=lambda item: (-item.robustness_score.overall_score, item.candidate_id),
            )
        )
        checksums = {
            "run": _hash_payload(
                {
                    "run_id": run_id,
                    "strategy_name": strategy_name,
                    "candidate_ordering": candidate_ordering,
                    "split_ids": [split.split_id for split in cpcv.splits],
                    "seed": random_seed,
                    "software_git_commit": software_git_commit,
                    "schema_version": schema_version,
                }
            ),
            "candidate_results": [
                _hash_payload({"candidate_id": item.candidate_id, "tier": item.tier.value})
                for item in candidate_results
            ],
        }
        return ValidationRunResult(
            run_id=run_id,
            strategy_name=strategy_name,
            candidate_ordering=candidate_ordering,
            candidate_results=tuple(candidate_results),
            cpcv=cpcv,
            comparison=comparison,
            checksums=checksums,
            software_git_commit=software_git_commit,
            schema_version=schema_version,
            random_seed=random_seed,
        )

    def _group_records(
        self, records: Sequence[ValidationRecord], n_groups: int
    ) -> list[list[ValidationRecord]]:
        groups: list[list[ValidationRecord]] = [[] for _ in range(n_groups)]
        for index, record in enumerate(records):
            groups[index % n_groups].append(record)
        return groups

    def _apply_leakage_filters(
        self,
        train_records: Sequence[ValidationRecord],
        *,
        test_start: datetime,
        test_end: datetime,
        purge_start: datetime | None,
        embargo_end: datetime | None,
        symbol_aware: bool,
        regime_aware: bool,
    ) -> tuple[list[ValidationRecord], list[str]]:
        filtered: list[ValidationRecord] = []
        warnings: list[str] = []
        test_symbols = {record.symbol for record in train_records if record.timestamp >= test_start}
        test_regimes = {record.regime for record in train_records if record.timestamp >= test_start}
        for record in train_records:
            if record.label_end_timestamp and record.label_end_timestamp >= test_start:
                warnings.append("overlapping-label leakage prevented")
                continue
            if purge_start and record.timestamp >= purge_start and record.timestamp <= test_end:
                warnings.append("purge leakage prevented")
                continue
            if embargo_end and record.timestamp > test_end and record.timestamp <= embargo_end:
                warnings.append("embargo leakage prevented")
                continue
            if (
                record.volatility_snapshot_timestamp
                and record.volatility_snapshot_timestamp > test_start
            ):
                warnings.append("volatility-surface leakage prevented")
                continue
            if record.earnings_event_timestamp and record.earnings_event_timestamp > test_start:
                warnings.append("future earnings-event leakage prevented")
                continue
            if record.corporate_action_timestamp and record.corporate_action_timestamp > test_start:
                warnings.append("corporate-action leakage prevented")
                continue
            if record.calibration_timestamp and record.calibration_timestamp > test_start:
                warnings.append("future calibration information prevented")
                continue
            if symbol_aware and record.symbol in test_symbols:
                warnings.append("symbol-aware leakage prevented")
                continue
            if regime_aware and record.regime in test_regimes:
                warnings.append("regime-aware leakage prevented")
                continue
            filtered.append(record)
        if not filtered:
            warnings.append("all training records were filtered out by leakage controls")
        return filtered, warnings

    def _split_id(self, train_group_ids: tuple[int, ...], test_group_ids: tuple[int, ...]) -> str:
        return "cpcv-" + "-".join(str(item) for item in train_group_ids + test_group_ids)


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    size = len(ordered)
    middle = size // 2
    if size % 2 == 0:
        return (ordered[middle - 1] + ordered[middle]) / 2.0
    return ordered[middle]


def _stddev(values: Sequence[float]) -> float:
    if len(values) <= 1:
        return 0.0
    mean_value = _mean(values)
    variance = sum((value - mean_value) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(max(variance, 0.0))


def _max_drawdown(values: Sequence[float]) -> float:
    peak = 0.0
    max_drop = 0.0
    running = 0.0
    for value in values:
        running += value
        peak = max(peak, running)
        max_drop = min(max_drop, running - peak)
    return abs(max_drop)


def _skewness(values: Sequence[float]) -> float:
    if len(values) <= 2:
        return 0.0
    mean_value = _mean(values)
    stdev = _stddev(values)
    if stdev == 0.0:
        return 0.0
    return sum(((value - mean_value) / stdev) ** 3 for value in values) / len(values)


def _kurtosis(values: Sequence[float]) -> float:
    if len(values) <= 3:
        return 3.0
    mean_value = _mean(values)
    stdev = _stddev(values)
    if stdev == 0.0:
        return 3.0
    return sum(((value - mean_value) / stdev) ** 4 for value in values) / len(values)


def _sharpe_uncertainty(
    observed_sharpe: float, skewness: float, kurtosis: float, sample_size: int
) -> float:
    numerator = 1.0 - skewness * observed_sharpe + ((kurtosis - 1.0) / 4.0) * (observed_sharpe**2)
    return math.sqrt(max(numerator, 1e-12) / max(sample_size - 1, 1))


def _extreme_value_quantile(number_of_trials: int) -> float:
    return NormalDist().inv_cdf(1.0 - 1.0 / max(number_of_trials, 2))


def _default_dsr_assumptions() -> tuple[str, ...]:
    return (
        "Sharpe uncertainty estimated from sample skewness and kurtosis",
        "selection bias approximated via expected maximum Sharpe under normal order statistics",
        "returns treated as stationary for the DSR approximation",
    )


def _logit_rank(rank: int, total: int) -> float:
    numerator = max(rank - 0.5, 1e-12)
    denominator = max(total - rank + 0.5, 1e-12)
    return math.log(numerator / denominator)


def _fold_metric(fold: ValidationFoldMetric, metric_key: str, *, in_sample: bool) -> float:
    mapping = {
        "expected_value": fold.train_expected_value if in_sample else fold.test_expected_value,
        "sharpe": fold.train_sharpe if in_sample else fold.test_sharpe,
        "pop": fold.train_return if in_sample else fold.test_return,
        "return": fold.train_return if in_sample else fold.test_return,
        "score": fold.in_sample_score if in_sample else fold.out_of_sample_score,
    }
    return mapping.get(metric_key, fold.in_sample_score if in_sample else fold.out_of_sample_score)


def _holm(values: Sequence[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    adjusted = [0.0] * len(values)
    running = 0.0
    for index, (original_index, value) in enumerate(ordered, start=1):
        candidate = min(1.0, (len(values) - index + 1) * value)
        running = max(running, candidate)
        adjusted[original_index] = running
    return adjusted


def _benjamini_hochberg(values: Sequence[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    adjusted = [0.0] * len(values)
    running = 1.0
    for index in range(len(ordered), 0, -1):
        original_index, value = ordered[index - 1]
        candidate = min(1.0, value * len(values) / index)
        running = min(running, candidate)
        adjusted[original_index] = running
    return adjusted


def _percentile_interval(
    values: Sequence[float], lower: float = 0.05, upper: float = 0.95
) -> tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    ordered = sorted(values)
    low_index = int(round((len(ordered) - 1) * lower))
    high_index = int(round((len(ordered) - 1) * upper))
    return ordered[low_index], ordered[high_index]


def _block_bootstrap(values: Sequence[float], *, block_size: int, rng: Random) -> list[float]:
    sample: list[float] = []
    while len(sample) < len(values):
        start = rng.randrange(len(values))
        block = [values[(start + offset) % len(values)] for offset in range(block_size)]
        sample.extend(block)
    return sample[: len(values)]


def _stationary_bootstrap(values: Sequence[float], *, block_size: int, rng: Random) -> list[float]:
    sample: list[float] = []
    position = rng.randrange(len(values))
    while len(sample) < len(values):
        if rng.random() < 1.0 / max(block_size, 1):
            position = rng.randrange(len(values))
        sample.append(values[position])
        position = (position + 1) % len(values)
    return sample


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _split_stability(cpcv: CPCVResult) -> float:
    if not cpcv.splits:
        return 0.0
    stable_splits = sum(1 for split in cpcv.splits if not split.leakage_warnings)
    return stable_splits / len(cpcv.splits)


def _trend(values: Sequence[float]) -> float:
    if len(values) <= 1:
        return 0.0
    x_values = list(range(len(values)))
    x_mean = _mean(x_values)
    y_mean = _mean(values)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values, strict=False))
    denominator = sum((x - x_mean) ** 2 for x in x_values)
    return 0.0 if denominator == 0.0 else numerator / denominator


def _neighbor_values(
    parameter: ParameterDefinition, current_value: Any, radius: int
) -> tuple[Any, ...]:
    if isinstance(parameter, IntegerRangeParameter):
        int_values = tuple(
            int(item)
            for item in range(
                max(parameter.minimum, int(current_value) - parameter.step * radius),
                min(parameter.maximum, int(current_value) + parameter.step * radius) + 1,
                parameter.step,
            )
        )
        return int_values
    if isinstance(parameter, FloatRangeParameter):
        low = max(parameter.minimum, float(current_value) - parameter.step * radius)
        high = min(parameter.maximum, float(current_value) + parameter.step * radius)
        steps = int(round((high - low) / parameter.step))
        return tuple(
            round(low + parameter.step * offset, parameter.precision) for offset in range(steps + 1)
        )
    if isinstance(parameter, CategoricalParameter):
        return tuple(parameter.choices)
    if isinstance(parameter, BooleanParameter):
        return (False, True)
    if isinstance(parameter, OrderedDiscreteParameter):
        values = tuple(parameter.values)
        if current_value in values:
            index = values.index(current_value)
            low = max(0, index - radius)
            high = min(len(values) - 1, index + radius)
            return values[low : high + 1]
        return values
    return (current_value,)


def _neighbor_values_for_result(
    parameter_space: ParameterSpace, parameter_name: str, value: Any
) -> tuple[Any, ...]:
    parameter = next(item for item in parameter_space.parameters if item.name == parameter_name)
    return _neighbor_values(parameter, value, 1)


def _build_neighbors(
    parameters: dict[str, float | int | str | bool],
    parameter_space: ParameterSpace,
    radius: int,
) -> list[dict[str, float | int | str | bool]]:
    neighbors = [dict(parameters)]
    for parameter in parameter_space.parameters:
        current_value = parameters.get(parameter.name)
        for value in _neighbor_values(parameter, current_value, radius):
            if value == current_value:
                continue
            neighbor = dict(parameters)
            neighbor[parameter.name] = value
            neighbors.append(neighbor)
    return neighbors


def _hash_payload(payload: dict[str, Any]) -> str:
    from hashlib import sha256

    return sha256(repr(payload).encode("utf-8")).hexdigest()
