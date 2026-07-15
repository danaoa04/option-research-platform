"""Deterministic parameter-space expansion and validation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from itertools import islice, product

from .exceptions import CandidateGenerationError, OptimizationValidationError
from .models import (
    BooleanParameter,
    Candidate,
    CategoricalParameter,
    DependentParameterRule,
    FloatRangeParameter,
    ForbiddenParameterCombination,
    IntegerRangeParameter,
    OrderedDiscreteParameter,
    ParameterSpace,
)

CustomRuleEvaluator = Callable[[str, dict[str, float | int | str | bool]], tuple[bool, str | None]]


@dataclass(slots=True)
class ParameterSpaceGenerator:
    custom_rule_evaluator: CustomRuleEvaluator | None = None

    def generate_exhaustive(self, space: ParameterSpace) -> list[Candidate]:
        self._validate_parameter_space(space)
        keys = sorted(param.name for param in space.parameters)
        domains = [self._domain_for_param(space, key) for key in keys]

        generated: list[Candidate] = []
        for index, combo in enumerate(product(*domains), start=1):
            params = {key: value for key, value in zip(keys, combo, strict=True)}
            filtered = self._apply_conditionals(space, params)
            if filtered is None:
                continue
            if not self._passes_dependencies(space.dependencies, filtered):
                continue
            if self._forbidden_reason(space.forbidden_combinations, filtered) is not None:
                continue
            if not self._passes_custom_rules(space, filtered):
                continue
            generated.append(Candidate(candidate_id=f"cand-{index:07d}", parameters=filtered))
            if space.max_candidates is not None and len(generated) >= space.max_candidates:
                break
        return generated

    def generate_low_discrepancy_placeholder(
        self,
        space: ParameterSpace,
        *,
        count: int,
        seed: int = 0,
    ) -> list[Candidate]:
        if count <= 0:
            return []
        exhaustive = self.generate_exhaustive(space)
        if not exhaustive:
            return []

        # Deterministic pseudo-random-like ordering without stochastic drift.
        step = max(1, len(exhaustive) // max(1, count))
        offset = seed % len(exhaustive)
        selected: list[Candidate] = []
        idx = offset
        for pick in range(count):
            selected.append(
                Candidate(
                    candidate_id=f"ld-{pick + 1:07d}",
                    parameters=dict(exhaustive[idx].parameters),
                )
            )
            idx = (idx + step) % len(exhaustive)
        return selected

    def coarse_to_fine(
        self,
        space: ParameterSpace,
        *,
        top_candidates: list[Candidate],
        refinement_width: int = 1,
        candidate_limit: int | None = None,
    ) -> list[Candidate]:
        if refinement_width < 0:
            raise CandidateGenerationError("refinement_width must be non-negative")
        if not top_candidates:
            return []

        refined: list[Candidate] = []
        keys = sorted(param.name for param in space.parameters)
        parameter_map = {param.name: param for param in space.parameters}

        for parent in top_candidates:
            domains: list[tuple[float | int | str | bool, ...]] = []
            for key in keys:
                param = parameter_map[key]
                parent_value = parent.parameters[key]
                domains.append(self._local_domain(param, parent_value, refinement_width))

            for combo in product(*domains):
                params = {key: value for key, value in zip(keys, combo, strict=True)}
                filtered = self._apply_conditionals(space, params)
                if filtered is None:
                    continue
                if not self._passes_dependencies(space.dependencies, filtered):
                    continue
                if self._forbidden_reason(space.forbidden_combinations, filtered) is not None:
                    continue
                if not self._passes_custom_rules(space, filtered):
                    continue
                refined.append(
                    Candidate(
                        candidate_id=f"ref-{len(refined) + 1:07d}",
                        parameters=filtered,
                    )
                )

        ordered = list(
            islice(
                self._dedupe_candidates(refined),
                candidate_limit if candidate_limit is not None else None,
            )
        )
        return ordered

    def _domain_for_param(
        self,
        space: ParameterSpace,
        name: str,
    ) -> tuple[float | int | str | bool, ...]:
        param = next((item for item in space.parameters if item.name == name), None)
        if param is None:
            raise CandidateGenerationError(f"parameter '{name}' not found")

        if isinstance(param, IntegerRangeParameter):
            return tuple(range(param.minimum, param.maximum + 1, param.step))
        if isinstance(param, FloatRangeParameter):
            steps = int(round((param.maximum - param.minimum) / param.step))
            values = [
                round(param.minimum + (i * param.step), param.precision) for i in range(steps + 1)
            ]
            return tuple(values)
        if isinstance(param, CategoricalParameter):
            return tuple(param.choices)
        if isinstance(param, BooleanParameter):
            return (False, True)
        if isinstance(param, OrderedDiscreteParameter):
            return tuple(param.values)
        raise CandidateGenerationError(f"unsupported parameter type for '{name}'")

    def _local_domain(
        self,
        param: IntegerRangeParameter
        | FloatRangeParameter
        | CategoricalParameter
        | BooleanParameter
        | OrderedDiscreteParameter,
        parent_value: float | int | str | bool,
        width: int,
    ) -> tuple[float | int | str | bool, ...]:
        if isinstance(param, IntegerRangeParameter):
            assert isinstance(parent_value, int)
            int_low = int(max(param.minimum, parent_value - (param.step * width)))
            int_high = int(min(param.maximum, parent_value + (param.step * width)))
            return tuple(range(int_low, int_high + 1, param.step))

        if isinstance(param, FloatRangeParameter):
            assert isinstance(parent_value, float)
            float_low = max(param.minimum, parent_value - (param.step * width))
            float_high = min(param.maximum, parent_value + (param.step * width))
            steps = int(round((float_high - float_low) / param.step))
            return tuple(
                round(float_low + (i * param.step), param.precision) for i in range(steps + 1)
            )

        if isinstance(param, CategoricalParameter):
            return tuple(param.choices)
        if isinstance(param, BooleanParameter):
            return (False, True)
        if isinstance(param, OrderedDiscreteParameter):
            values = tuple(param.values)
            try:
                idx = values.index(parent_value)
            except ValueError:
                return values
            low = max(0, idx - width)
            high = min(len(values) - 1, idx + width)
            return values[low : high + 1]

        raise CandidateGenerationError("unsupported parameter definition")

    def _validate_parameter_space(self, space: ParameterSpace) -> None:
        names = [param.name for param in space.parameters]
        if len(names) != len(set(names)):
            raise OptimizationValidationError("parameter names must be unique")

        for param in space.parameters:
            if isinstance(param, IntegerRangeParameter):
                if param.step <= 0:
                    raise OptimizationValidationError(f"parameter '{param.name}' step must be > 0")
                if param.minimum > param.maximum:
                    raise OptimizationValidationError(
                        f"parameter '{param.name}' minimum must be <= maximum"
                    )
            elif isinstance(param, FloatRangeParameter):
                if param.step <= 0:
                    raise OptimizationValidationError(f"parameter '{param.name}' step must be > 0")
                if param.minimum > param.maximum:
                    raise OptimizationValidationError(
                        f"parameter '{param.name}' minimum must be <= maximum"
                    )
            elif isinstance(param, CategoricalParameter):
                if not param.choices:
                    raise OptimizationValidationError(
                        f"parameter '{param.name}' requires at least one categorical choice"
                    )
            elif isinstance(param, OrderedDiscreteParameter) and not param.values:
                raise OptimizationValidationError(
                    f"parameter '{param.name}' requires at least one ordered value"
                )

    def _apply_conditionals(
        self,
        space: ParameterSpace,
        params: dict[str, float | int | str | bool],
    ) -> dict[str, float | int | str | bool] | None:
        filtered = dict(params)
        for conditional in space.conditionals:
            dependency_value = filtered.get(conditional.depends_on)
            if dependency_value in conditional.allowed_values:
                continue
            filtered.pop(conditional.parameter, None)
        return filtered

    def _passes_dependencies(
        self,
        rules: tuple[DependentParameterRule, ...],
        params: dict[str, float | int | str | bool],
    ) -> bool:
        for rule in rules:
            left = params.get(rule.left_parameter)
            right = params.get(rule.right_parameter)
            if left is None or right is None:
                return False

            if rule.operator == "<" and not (float(left) < float(right)):
                return False
            if rule.operator == "<=" and not (float(left) <= float(right)):
                return False
            if rule.operator == ">" and not (float(left) > float(right)):
                return False
            if rule.operator == ">=" and not (float(left) >= float(right)):
                return False
            if rule.operator == "==" and not (left == right):
                return False
        return True

    def _forbidden_reason(
        self,
        rules: tuple[ForbiddenParameterCombination, ...],
        params: dict[str, float | int | str | bool],
    ) -> str | None:
        for rule in rules:
            if all(params.get(key) == value for key, value in rule.values.items()):
                return rule.reason
        return None

    def _passes_custom_rules(
        self,
        space: ParameterSpace,
        params: dict[str, float | int | str | bool],
    ) -> bool:
        if self.custom_rule_evaluator is None:
            return True
        for rule in space.custom_rules:
            passed, _reason = self.custom_rule_evaluator(rule.name, params)
            if not passed:
                return False
        return True

    def _dedupe_candidates(self, candidates: list[Candidate]) -> list[Candidate]:
        deduped: list[Candidate] = []
        seen: set[tuple[tuple[str, float | int | str | bool], ...]] = set()
        for item in candidates:
            key = tuple(sorted(item.parameters.items()))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped
