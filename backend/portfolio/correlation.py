"""Deterministic correlation estimation for portfolio construction."""

from __future__ import annotations

from dataclasses import dataclass

from .models import CandidateInput, CorrelationEstimate, CorrelationKind


@dataclass(slots=True)
class CorrelationEngine:
    min_samples: int = 20
    shrinkage: float = 0.1

    def estimate(
        self,
        candidates: tuple[CandidateInput, ...],
        kind: CorrelationKind,
    ) -> tuple[CorrelationEstimate, ...]:
        output: list[CorrelationEstimate] = []
        ordered = tuple(sorted(candidates, key=lambda item: item.candidate_id))

        for left_index, left in enumerate(ordered):
            left_values = self._series_for_kind(left, kind)
            for right in ordered[left_index:]:
                right_values = self._series_for_kind(right, kind)
                sample_count = min(len(left_values), len(right_values))
                sparse = sample_count < self.min_samples
                if sample_count == 0:
                    corr = 0.0
                    uncertainty = 1.0
                else:
                    corr = _corr(left_values[:sample_count], right_values[:sample_count])
                    corr = (1.0 - self.shrinkage) * corr
                    uncertainty = 1.0 / max(sample_count, 1)
                    if sparse:
                        uncertainty = max(uncertainty, 0.4)

                output.append(
                    CorrelationEstimate(
                        left_id=left.candidate_id,
                        right_id=right.candidate_id,
                        kind=kind,
                        value=corr,
                        uncertainty=uncertainty,
                        effective_sample_size=sample_count,
                        sparse_warning=sparse,
                    )
                )
        return tuple(output)

    def matrix(
        self,
        estimates: tuple[CorrelationEstimate, ...],
    ) -> dict[str, dict[str, float]]:
        ids = sorted({item.left_id for item in estimates} | {item.right_id for item in estimates})
        matrix: dict[str, dict[str, float]] = {item: {other: 0.0 for other in ids} for item in ids}
        for estimate in estimates:
            matrix[estimate.left_id][estimate.right_id] = estimate.value
            matrix[estimate.right_id][estimate.left_id] = estimate.value
        for item in ids:
            matrix[item][item] = 1.0
        return matrix

    def _series_for_kind(
        self, candidate: CandidateInput, kind: CorrelationKind
    ) -> tuple[float, ...]:
        if kind == CorrelationKind.STRATEGY_RETURN:
            return candidate.returns
        if kind == CorrelationKind.UNDERLYING_RETURN:
            return candidate.underlying_returns
        if kind == CorrelationKind.PNL:
            return candidate.pnl
        if kind == CorrelationKind.DRAWDOWN:
            return candidate.drawdowns
        if kind == CorrelationKind.TAIL_LOSS:
            return candidate.tail_losses
        if kind == CorrelationKind.DOWNSIDE:
            return tuple(value for value in candidate.returns if value < 0.0)
        if kind == CorrelationKind.REGIME_CONDITIONED:
            return candidate.returns
        if kind == CorrelationKind.ROLLING:
            window = min(10, len(candidate.returns))
            if window <= 1:
                return candidate.returns
            return tuple(
                sum(candidate.returns[index : index + window]) / window
                for index in range(len(candidate.returns) - window + 1)
            )
        return candidate.returns


def _corr(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) <= 1 or len(right) <= 1:
        return 0.0
    mean_left = sum(left) / len(left)
    mean_right = sum(right) / len(right)
    cov = sum(
        (left_value - mean_left) * (right_value - mean_right)
        for left_value, right_value in zip(left, right, strict=False)
    ) / max(len(left) - 1, 1)
    var_left = sum((value - mean_left) ** 2 for value in left) / max(len(left) - 1, 1)
    var_right = sum((value - mean_right) ** 2 for value in right) / max(len(right) - 1, 1)
    if var_left <= 0.0 or var_right <= 0.0:
        return 0.0
    return float(max(-1.0, min(1.0, cov / ((var_left * var_right) ** 0.5))))
