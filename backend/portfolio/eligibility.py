"""Candidate eligibility filters for portfolio construction."""

from __future__ import annotations

from dataclasses import dataclass

from .models import CandidateInput, EligibilityPolicy, EligibilityRejection


@dataclass(slots=True)
class EligibilityEngine:
    def filter_candidates(
        self,
        candidates: tuple[CandidateInput, ...],
        policy: EligibilityPolicy,
    ) -> tuple[tuple[CandidateInput, ...], tuple[EligibilityRejection, ...]]:
        eligible: list[CandidateInput] = []
        rejected: list[EligibilityRejection] = []
        allowed_promotions = set(policy.allowed_promotions)

        for candidate in candidates:
            validation = candidate.validation
            reasons: list[str] = []
            if validation.promotion_status not in allowed_promotions:
                reasons.append("promotion_status")
            if validation.robustness_score < policy.minimum_robustness:
                reasons.append("minimum_robustness")
            if validation.pbo > policy.maximum_pbo:
                reasons.append("maximum_pbo")
            if validation.deflated_sharpe < policy.minimum_deflated_sharpe:
                reasons.append("minimum_deflated_sharpe")
            if validation.out_of_sample_fold_count < policy.minimum_out_of_sample_folds:
                reasons.append("minimum_out_of_sample_folds")
            if validation.calibration_error > policy.maximum_calibration_error:
                reasons.append("maximum_calibration_error")
            if validation.sample_size < policy.minimum_sample_size:
                reasons.append("minimum_sample_size")
            if validation.parameter_stability < policy.minimum_parameter_stability:
                reasons.append("minimum_parameter_stability")
            if validation.regime_coverage < policy.minimum_regime_coverage:
                reasons.append("minimum_regime_coverage")
            if validation.stress_degradation < policy.minimum_stress_resilience:
                reasons.append("minimum_stress_resilience")
            if validation.liquidity < policy.minimum_liquidity:
                reasons.append("minimum_liquidity")
            if validation.data_quality < policy.minimum_data_quality:
                reasons.append("minimum_data_quality")
            if policy.exclude_unresolved_warnings and validation.unresolved_warnings:
                reasons.append("unresolved_warnings")
            if policy.exclude_unresolved_failures and validation.unresolved_failures:
                reasons.append("unresolved_failures")

            if reasons:
                rejected.append(
                    EligibilityRejection(
                        candidate_id=candidate.candidate_id, reasons=tuple(reasons)
                    )
                )
            else:
                eligible.append(candidate)

        eligible.sort(key=lambda item: item.candidate_id)
        rejected.sort(key=lambda item: item.candidate_id)
        return tuple(eligible), tuple(rejected)
