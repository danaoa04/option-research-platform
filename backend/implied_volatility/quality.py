"""Quality scoring for implied-volatility observations and surface hygiene."""

from __future__ import annotations

from dataclasses import dataclass

from .models import (
    IVSolverStatus,
    ObservationQualityResult,
    QualityComponentScore,
    QualityReasonCode,
    QualityScoringConfig,
    VolatilityObservationRecord,
)


@dataclass(slots=True)
class ObservationQualityScorer:
    """Compute component and aggregate quality scores without dropping raw rows."""

    def score(
        self,
        observation: VolatilityObservationRecord,
        *,
        neighbor_iv_jump: float | None = None,
        duplicate_contract: bool = False,
    ) -> ObservationQualityResult:
        config = self._default_config()
        components: list[QualityComponentScore] = []

        def add(
            code: QualityReasonCode,
            triggered: bool,
            details: str | None = None,
            severity: float = 1.0,
        ) -> None:
            weight = config.score_weights.get(code, 1.0)
            score = 1.0 if not triggered else max(0.0, 1.0 - severity)
            components.append(
                QualityComponentScore(
                    reason_code=code,
                    score=score,
                    weight=weight,
                    triggered=triggered,
                    details=details,
                )
            )

        add(
            QualityReasonCode.SOLVER_NON_CONVERGED,
            observation.solver_status
            not in {IVSolverStatus.SUCCESS, IVSolverStatus.APPROXIMATE},
            details=f"solver_status={observation.solver_status.value}",
        )

        bound_flag = (
            "below_intrinsic" in observation.quality_flags
            or "above_theoretical" in observation.quality_flags
        )
        add(QualityReasonCode.ARBITRAGE_BOUNDS, bound_flag)

        crossed = (
            observation.bid is not None
            and observation.ask is not None
            and observation.bid > observation.ask
        )
        add(QualityReasonCode.CROSSED_MARKET, crossed)

        add(QualityReasonCode.ZERO_BID, observation.bid == 0.0)
        add(QualityReasonCode.MISSING_ASK, observation.ask is None)

        if (
            observation.spread_width is not None
            and observation.midpoint is not None
            and observation.midpoint > 0.0
        ):
            rel_spread = observation.spread_width / observation.midpoint
        else:
            rel_spread = 0.0
        add(
            QualityReasonCode.WIDE_SPREAD,
            rel_spread > config.max_relative_spread,
            details=f"relative_spread={rel_spread:.6f}",
            severity=min(rel_spread, 1.0),
        )

        add(
            QualityReasonCode.STALE_QUOTE,
            (observation.stale_age_seconds or 0.0) > config.stale_quote_seconds,
            details=f"stale_age_seconds={observation.stale_age_seconds}",
        )

        add(
            QualityReasonCode.LOW_VOLUME,
            (observation.volume or 0) < config.min_volume,
            details=f"volume={observation.volume}",
        )
        add(
            QualityReasonCode.LOW_OPEN_INTEREST,
            (observation.open_interest or 0) < config.min_open_interest,
            details=f"open_interest={observation.open_interest}",
        )

        add(
            QualityReasonCode.LOW_VEGA,
            observation.vega is not None and observation.vega < config.min_vega,
            details=f"vega={observation.vega}",
        )

        add(
            QualityReasonCode.EXCESSIVE_PRICING_ERROR,
            observation.pricing_error is not None
            and abs(observation.pricing_error) > config.max_pricing_error,
            details=f"pricing_error={observation.pricing_error}",
        )

        add(
            QualityReasonCode.TREE_SENSITIVITY,
            observation.tree_sensitivity is not None
            and observation.tree_sensitivity > config.max_tree_sensitivity,
            details=f"tree_sensitivity={observation.tree_sensitivity}",
        )

        add(
            QualityReasonCode.APPROXIMATE_MODEL,
            observation.solver_status == IVSolverStatus.APPROXIMATE,
        )

        add(
            QualityReasonCode.MISSING_CONTRACT_METADATA,
            not observation.contract_metadata,
        )

        add(
            QualityReasonCode.INCONSISTENT_NEIGHBOR,
            neighbor_iv_jump is not None and neighbor_iv_jump > config.neighbor_iv_jump_threshold,
            details=f"neighbor_iv_jump={neighbor_iv_jump}",
        )

        add(QualityReasonCode.DUPLICATE_CONTRACT, duplicate_contract)

        total_weight = sum(component.weight for component in components) or 1.0
        weighted = sum(component.score * component.weight for component in components)
        overall_score = weighted / total_weight
        reasons = tuple(component.reason_code for component in components if component.triggered)
        warnings = tuple(
            f"{component.reason_code.value}: {component.details or 'triggered'}"
            for component in components
            if component.triggered
        )
        exclusion = overall_score < config.min_acceptable_score or any(
            code
            in {
                QualityReasonCode.SOLVER_NON_CONVERGED,
                QualityReasonCode.ARBITRAGE_BOUNDS,
                QualityReasonCode.CROSSED_MARKET,
                QualityReasonCode.MISSING_ASK,
            }
            for code in reasons
        )

        return ObservationQualityResult(
            overall_score=overall_score,
            component_scores=tuple(components),
            exclusion_recommendation=exclusion,
            warnings=warnings,
            reason_codes=reasons,
        )

    def _default_config(self) -> QualityScoringConfig:
        return QualityScoringConfig(
            score_weights={
                QualityReasonCode.SOLVER_NON_CONVERGED: 3.0,
                QualityReasonCode.ARBITRAGE_BOUNDS: 3.0,
                QualityReasonCode.CROSSED_MARKET: 2.0,
                QualityReasonCode.MISSING_ASK: 2.0,
                QualityReasonCode.WIDE_SPREAD: 1.5,
                QualityReasonCode.STALE_QUOTE: 1.5,
                QualityReasonCode.EXCESSIVE_PRICING_ERROR: 2.0,
                QualityReasonCode.TREE_SENSITIVITY: 1.5,
            }
        )
