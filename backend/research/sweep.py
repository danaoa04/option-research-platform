"""Deterministic exhaustive parameter sweep generation."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from .models import ParameterSweepCase, ParameterSweepGrid


@dataclass(slots=True)
class ParameterSweepEngine:
    def generate_cases(self, grid: ParameterSweepGrid) -> list[ParameterSweepCase]:
        if not grid.parameters:
            return []

        keys = sorted(grid.parameters)
        value_sets = [tuple(grid.parameters[key]) for key in keys]
        for values in value_sets:
            if not values:
                raise ValueError("all sweep parameters must have at least one value")

        cases: list[ParameterSweepCase] = []
        for index, combo in enumerate(product(*value_sets), start=1):
            params = {key: value for key, value in zip(keys, combo, strict=True)}
            cases.append(ParameterSweepCase(case_id=f"case-{index:06d}", parameters=params))
        return cases
