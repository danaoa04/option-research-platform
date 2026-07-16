"""Deterministic refinement and multi-metric ranking over sweep results."""

from __future__ import annotations

from dataclasses import dataclass

from .exceptions import RefinementError
from .models import ParameterSweepCase, ParameterSweepGrid


@dataclass(slots=True, frozen=True)
class ScoredSweepCase:
    case: ParameterSweepCase
    metrics: dict[str, float]


@dataclass(slots=True)
class DeterministicRefinementEngine:
    def coarse_to_fine(
        self,
        *,
        grid: ParameterSweepGrid,
        scored: list[ScoredSweepCase],
        objective: str,
        top_k: int = 3,
        step_scale: float = 0.5,
    ) -> ParameterSweepGrid:
        if not scored:
            raise RefinementError("scored cases cannot be empty")
        if objective == "":
            raise RefinementError("objective cannot be empty")

        ordered = sorted(
            scored,
            key=lambda row: (-float(row.metrics.get(objective, 0.0)), row.case.case_id),
        )
        top = ordered[: max(top_k, 1)]

        refined: dict[str, tuple[float | int | str, ...]] = {}
        for key, values in grid.parameters.items():
            if not values:
                raise RefinementError("parameter grid values cannot be empty")
            if all(isinstance(value, (int, float)) for value in values):
                center_values = [float(item.case.parameters[key]) for item in top]
                center = sum(center_values) / len(center_values)
                width = max(float(max(values)) - float(min(values)), 1.0)
                step = max(width * step_scale / max(len(values), 1), 1e-6)
                candidates = sorted({center - step, center, center + step})
                if all(isinstance(value, int) for value in values):
                    refined[key] = tuple(int(round(item)) for item in candidates)
                else:
                    refined[key] = tuple(candidates)
            else:
                refined[key] = tuple(sorted({item.case.parameters[key] for item in top}))

        return ParameterSweepGrid(parameters=refined)

    def constrained_filter(
        self,
        *,
        scored: list[ScoredSweepCase],
        constraints: dict[str, tuple[float | None, float | None]],
    ) -> list[ScoredSweepCase]:
        result: list[ScoredSweepCase] = []
        for item in scored:
            keep = True
            for metric, bounds in constraints.items():
                value = float(item.metrics.get(metric, 0.0))
                lower, upper = bounds
                if lower is not None and value < lower:
                    keep = False
                    break
                if upper is not None and value > upper:
                    keep = False
                    break
            if keep:
                result.append(item)
        return result

    def pareto_front(
        self,
        *,
        scored: list[ScoredSweepCase],
        objectives: dict[str, bool],
    ) -> list[ScoredSweepCase]:
        if not scored:
            return []

        def dominates(left: ScoredSweepCase, right: ScoredSweepCase) -> bool:
            better_or_equal = True
            strictly_better = False
            for metric, maximize in objectives.items():
                left_value = float(left.metrics.get(metric, 0.0))
                right_value = float(right.metrics.get(metric, 0.0))
                if maximize:
                    if left_value < right_value:
                        better_or_equal = False
                        break
                    if left_value > right_value:
                        strictly_better = True
                else:
                    if left_value > right_value:
                        better_or_equal = False
                        break
                    if left_value < right_value:
                        strictly_better = True
            return better_or_equal and strictly_better

        front: list[ScoredSweepCase] = []
        for candidate in scored:
            if any(dominates(other, candidate) for other in scored if other is not candidate):
                continue
            front.append(candidate)
        return sorted(front, key=lambda row: row.case.case_id)

    def deterministic_rank(
        self,
        *,
        scored: list[ScoredSweepCase],
        objectives: dict[str, bool],
    ) -> list[ScoredSweepCase]:
        weights = {metric: 1.0 / max(len(objectives), 1) for metric in objectives}

        def score(item: ScoredSweepCase) -> float:
            total = 0.0
            for metric, maximize in objectives.items():
                value = float(item.metrics.get(metric, 0.0))
                total += weights[metric] * (value if maximize else -value)
            return total

        return sorted(scored, key=lambda item: (-score(item), item.case.case_id))
