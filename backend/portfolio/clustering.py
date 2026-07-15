"""Risk-factor and correlation-aware clustering."""

from __future__ import annotations

from dataclasses import dataclass

from .models import CandidateInput, ClusterAssignment, CorrelationEstimate


@dataclass(slots=True)
class RiskClusterEngine:
    correlation_threshold: float = 0.75

    def assign(
        self,
        candidates: tuple[CandidateInput, ...],
        correlations: tuple[CorrelationEstimate, ...],
    ) -> tuple[ClusterAssignment, ...]:
        by_id = {item.candidate_id: item for item in candidates}
        corr_map = {
            (item.left_id, item.right_id): item
            for item in correlations
            if item.left_id != item.right_id
        }
        output: list[ClusterAssignment] = []

        for candidate_id in sorted(by_id):
            candidate = by_id[candidate_id]
            reasons = [
                f"symbol:{candidate.exposure.symbol}",
                f"sector:{candidate.exposure.sector}",
                f"family:{candidate.exposure.strategy_family}",
                f"expiry:{candidate.exposure.expiration_bucket}",
                f"vol_regime:{candidate.exposure.volatility_regime}",
                f"term_regime:{candidate.exposure.term_structure_regime}",
            ]
            directional = "long_delta" if candidate.exposure.delta >= 0.0 else "short_delta"
            reasons.append(f"direction:{directional}")
            if candidate.exposure.earnings_exposure > 0.0:
                reasons.append("earnings:yes")
            if abs(candidate.exposure.vega) >= 0.2:
                reasons.append("vega_profile:material")
            if abs(candidate.exposure.gamma) >= 0.1:
                reasons.append("gamma_profile:material")

            high_corr_hits = 0
            for other_id in by_id:
                if other_id == candidate_id:
                    continue
                direct = corr_map.get((candidate_id, other_id)) or corr_map.get(
                    (other_id, candidate_id)
                )
                if (
                    direct
                    and direct.value >= self.correlation_threshold
                    and not direct.sparse_warning
                ):
                    high_corr_hits += 1
            reasons.append(f"high_corr_neighbors:{high_corr_hits}")

            cluster_id = (
                f"{candidate.exposure.symbol}|{candidate.exposure.strategy_family}|"
                f"{candidate.exposure.expiration_bucket}|{candidate.exposure.volatility_regime}"
            )
            confidence = min(1.0, 0.5 + high_corr_hits * 0.1)
            output.append(
                ClusterAssignment(
                    candidate_id=candidate_id,
                    cluster_id=cluster_id,
                    confidence=confidence,
                    reasons=tuple(reasons),
                )
            )

        return tuple(output)
