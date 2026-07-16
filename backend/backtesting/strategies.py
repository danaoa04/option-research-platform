"""Generic multi-leg strategy definitions, templates, and selection policies."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Any


class LegKind(StrEnum):
    CALL = "call"
    PUT = "put"
    STOCK = "stock"
    CASH = "cash"


class LegDirection(StrEnum):
    BUY = "buy"
    SELL = "sell"


class LegEffect(StrEnum):
    OPEN = "open"
    CLOSE = "close"


class SelectionPolicyType(StrEnum):
    EXACT_STRIKE = "exact_strike"
    NEAREST_STRIKE = "nearest_strike"
    PERCENT_ITM_OTM = "percentage_itm_or_otm"
    TARGET_DELTA = "target_delta"
    TARGET_MONEYNESS = "target_moneyness"
    STANDARD_DEVIATION_DISTANCE = "standard_deviation_distance"
    TARGET_PREMIUM = "target_premium"
    EXPIRATION_EXACT_DATE = "expiration_exact_date"
    NEAREST_DTE = "nearest_dte"
    MINIMUM_DTE = "minimum_dte"
    MAXIMUM_DTE = "maximum_dte"
    WEEKLY_VS_MONTHLY = "weekly_vs_monthly_preference"
    LIQUIDITY = "liquidity_preference"
    QUALITY_SCORE = "quality_score_preference"


@dataclass(slots=True, frozen=True)
class LegSelectionPolicy:
    policy_type: SelectionPolicyType
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class MultiLegDefinitionLeg:
    label: str
    leg_kind: LegKind
    direction: LegDirection
    effect: LegEffect
    quantity_ratio: int
    contract_multiplier: int
    strike_policy: LegSelectionPolicy | None = None
    expiration_policy: LegSelectionPolicy | None = None
    delta_policy: LegSelectionPolicy | None = None
    moneyness_policy: LegSelectionPolicy | None = None
    dte_policy: LegSelectionPolicy | None = None
    exercise_style_requirement: str | None = None
    settlement_requirement: str | None = None
    leg_group: str | None = None
    entry_dependencies: tuple[str, ...] = ()
    exit_dependencies: tuple[str, ...] = ()
    roll_dependencies: tuple[str, ...] = ()
    optional: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class MultiLegStrategyDefinition:
    name: str
    legs: tuple[MultiLegDefinitionLeg, ...]
    validation_rules: tuple[dict[str, Any], ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class LegSelectionCandidate:
    contract_identifier: str
    strike: float | None
    expiration: date | None
    delta: float | None
    moneyness: float | None
    premium: float | None
    dte: int | None
    is_weekly: bool | None
    liquidity_score: float | None
    quality_score: float | None


@dataclass(slots=True, frozen=True)
class LegSelectionDiagnostic:
    policy: SelectionPolicyType
    reason_code: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class LegSelectionResult:
    candidate: LegSelectionCandidate | None
    diagnostics: tuple[LegSelectionDiagnostic, ...]


class StrategyDefinitionError(RuntimeError):
    """Raised when a strategy template or definition fails validation."""


def compile_template(
    *,
    template_name: str,
    metadata: dict[str, Any] | None = None,
) -> MultiLegStrategyDefinition:
    # Preserve legacy behavior for existing public template names.
    definition = _TEMPLATE_BUILDERS.get(template_name)
    if definition is not None:
        strategy = definition()
        if metadata:
            merged = dict(strategy.metadata)
            merged.update(metadata)
            strategy = MultiLegStrategyDefinition(
                name=strategy.name,
                legs=strategy.legs,
                validation_rules=strategy.validation_rules,
                metadata=merged,
            )
        validate_definition(strategy)
        return strategy

    # For non-legacy names, allow Sprint 8A strategy-library identifiers.
    try:
        from .strategy_library import (
            StrategyLibraryError,
            compile_strategy_template,
            default_strategy_template_registry,
        )

        try:
            return compile_strategy_template(
                template_name=template_name,
                metadata=metadata,
            )
        except StrategyLibraryError:
            registry = default_strategy_template_registry()
            match = next(
                (
                    item.canonical_identifier
                    for item in registry.discover(include_deprecated=True)
                    if item.name == template_name
                ),
                None,
            )
            if match is None:
                raise
            return compile_strategy_template(
                template_name=match,
                metadata=metadata,
                registry=registry,
            )
    except StrategyLibraryError as exc:
        raise StrategyDefinitionError(f"unknown strategy template: {template_name}") from exc
    except Exception as exc:
        raise StrategyDefinitionError(f"unknown strategy template: {template_name}") from exc


def validate_definition(definition: MultiLegStrategyDefinition) -> None:
    labels = {leg.label for leg in definition.legs}
    if len(labels) != len(definition.legs):
        raise StrategyDefinitionError("duplicate leg labels in strategy definition")
    for leg in definition.legs:
        if leg.quantity_ratio <= 0:
            raise StrategyDefinitionError(f"leg quantity ratio must be positive: {leg.label}")
        for dependency in (
            *leg.entry_dependencies,
            *leg.exit_dependencies,
            *leg.roll_dependencies,
        ):
            if dependency not in labels:
                raise StrategyDefinitionError(
                    "invalid dependency in strategy definition: "
                    f"leg={leg.label} dependency={dependency}"
                )


class LegSelectionEngine:
    def select_leg(
        self,
        *,
        candidates: tuple[LegSelectionCandidate, ...],
        policies: tuple[LegSelectionPolicy, ...],
    ) -> LegSelectionResult:
        filtered = list(candidates)
        diagnostics: list[LegSelectionDiagnostic] = []
        for policy in policies:
            filtered = self._apply_policy(policy=policy, candidates=tuple(filtered))
            if not filtered:
                diagnostics.append(
                    LegSelectionDiagnostic(
                        policy=policy.policy_type,
                        reason_code="no_candidates_after_policy",
                        details={"parameters": dict(policy.parameters)},
                    )
                )
                return LegSelectionResult(candidate=None, diagnostics=tuple(diagnostics))
        selected = filtered[0] if filtered else None
        return LegSelectionResult(candidate=selected, diagnostics=tuple(diagnostics))

    def _apply_policy(
        self,
        *,
        policy: LegSelectionPolicy,
        candidates: tuple[LegSelectionCandidate, ...],
    ) -> list[LegSelectionCandidate]:
        if policy.policy_type is SelectionPolicyType.EXACT_STRIKE:
            target = float(policy.parameters["strike"])
            return [item for item in candidates if item.strike == target]
        if policy.policy_type is SelectionPolicyType.NEAREST_STRIKE:
            target = float(policy.parameters["strike"])
            ranked = sorted(
                candidates,
                key=lambda row: abs((row.strike or 0.0) - target),
            )
            return ranked[:1]
        if policy.policy_type is SelectionPolicyType.TARGET_DELTA:
            target = float(policy.parameters["delta"])
            ranked = sorted(
                [item for item in candidates if item.delta is not None],
                key=lambda row: abs(_to_float(row.delta) - target),
            )
            return ranked[:1]
        if policy.policy_type is SelectionPolicyType.TARGET_MONEYNESS:
            target = float(policy.parameters["moneyness"])
            ranked = sorted(
                [item for item in candidates if item.moneyness is not None],
                key=lambda row: abs(_to_float(row.moneyness) - target),
            )
            return ranked[:1]
        if policy.policy_type is SelectionPolicyType.TARGET_PREMIUM:
            target = float(policy.parameters["premium"])
            ranked = sorted(
                [item for item in candidates if item.premium is not None],
                key=lambda row: abs(_to_float(row.premium) - target),
            )
            return ranked[:1]
        if policy.policy_type is SelectionPolicyType.EXPIRATION_EXACT_DATE:
            target = policy.parameters["expiration"]
            return [item for item in candidates if item.expiration == target]
        if policy.policy_type is SelectionPolicyType.NEAREST_DTE:
            target = int(policy.parameters["dte"])
            ranked = sorted(
                [item for item in candidates if item.dte is not None],
                key=lambda row: abs(_to_int(row.dte) - target),
            )
            return ranked[:1]
        if policy.policy_type is SelectionPolicyType.MINIMUM_DTE:
            threshold = int(policy.parameters["minimum_dte"])
            return [item for item in candidates if (item.dte or -1) >= threshold]
        if policy.policy_type is SelectionPolicyType.MAXIMUM_DTE:
            threshold = int(policy.parameters["maximum_dte"])
            return [item for item in candidates if (item.dte or 10**9) <= threshold]
        if policy.policy_type is SelectionPolicyType.WEEKLY_VS_MONTHLY:
            prefer_weekly = bool(policy.parameters.get("prefer_weekly", True))
            return [
                item
                for item in candidates
                if item.is_weekly is None or item.is_weekly is prefer_weekly
            ]
        if policy.policy_type is SelectionPolicyType.LIQUIDITY:
            minimum = float(policy.parameters.get("minimum_liquidity", 0.0))
            return [item for item in candidates if (item.liquidity_score or 0.0) >= minimum]
        if policy.policy_type is SelectionPolicyType.QUALITY_SCORE:
            minimum = float(policy.parameters.get("minimum_quality", 0.0))
            return [item for item in candidates if (item.quality_score or 0.0) >= minimum]
        if policy.policy_type is SelectionPolicyType.PERCENT_ITM_OTM:
            percent_threshold = float(policy.parameters.get("percent", 0.0))
            direction = str(policy.parameters.get("direction", "otm"))
            if direction == "itm":
                return [
                    item
                    for item in candidates
                    if item.moneyness is not None
                    and _to_float(item.moneyness) < (1 - percent_threshold)
                ]
            return [
                item
                for item in candidates
                if item.moneyness is not None
                and _to_float(item.moneyness) > (1 + percent_threshold)
            ]
        if policy.policy_type is SelectionPolicyType.STANDARD_DEVIATION_DISTANCE:
            target = float(policy.parameters.get("target_std_dev", 0.0))
            ranked = sorted(
                [item for item in candidates if item.moneyness is not None],
                key=lambda row: abs(_to_float(row.moneyness) - target),
            )
            return ranked[:1]
        return list(candidates)


def _single_leg(
    *,
    label: str,
    leg_kind: LegKind,
    direction: LegDirection,
    group: str,
) -> MultiLegDefinitionLeg:
    return MultiLegDefinitionLeg(
        label=label,
        leg_kind=leg_kind,
        direction=direction,
        effect=LegEffect.OPEN,
        quantity_ratio=1,
        contract_multiplier=100,
        leg_group=group,
    )


def _covered_call() -> MultiLegStrategyDefinition:
    return MultiLegStrategyDefinition(
        name="covered_call",
        legs=(
            _single_leg(
                label="stock_long",
                leg_kind=LegKind.STOCK,
                direction=LegDirection.BUY,
                group="stock",
            ),
            _single_leg(
                label="short_call",
                leg_kind=LegKind.CALL,
                direction=LegDirection.SELL,
                group="call_overlay",
            ),
        ),
    )


def _cash_secured_put() -> MultiLegStrategyDefinition:
    return MultiLegStrategyDefinition(
        name="cash_secured_put",
        legs=(
            _single_leg(
                label="cash_collateral",
                leg_kind=LegKind.CASH,
                direction=LegDirection.BUY,
                group="collateral",
            ),
            _single_leg(
                label="short_put",
                leg_kind=LegKind.PUT,
                direction=LegDirection.SELL,
                group="short_put",
            ),
        ),
    )


def _bull_put_spread() -> MultiLegStrategyDefinition:
    return MultiLegStrategyDefinition(
        name="bull_put_spread",
        legs=(
            _single_leg(
                label="short_put",
                leg_kind=LegKind.PUT,
                direction=LegDirection.SELL,
                group="short_leg",
            ),
            _single_leg(
                label="long_put",
                leg_kind=LegKind.PUT,
                direction=LegDirection.BUY,
                group="long_leg",
            ),
        ),
    )


def _bear_call_spread() -> MultiLegStrategyDefinition:
    return MultiLegStrategyDefinition(
        name="bear_call_spread",
        legs=(
            _single_leg(
                label="short_call",
                leg_kind=LegKind.CALL,
                direction=LegDirection.SELL,
                group="short_leg",
            ),
            _single_leg(
                label="long_call",
                leg_kind=LegKind.CALL,
                direction=LegDirection.BUY,
                group="long_leg",
            ),
        ),
    )


def _bull_call_spread() -> MultiLegStrategyDefinition:
    return MultiLegStrategyDefinition(
        name="bull_call_spread",
        legs=(
            _single_leg(
                label="long_call",
                leg_kind=LegKind.CALL,
                direction=LegDirection.BUY,
                group="long_leg",
            ),
            _single_leg(
                label="short_call",
                leg_kind=LegKind.CALL,
                direction=LegDirection.SELL,
                group="short_leg",
            ),
        ),
    )


def _bear_put_spread() -> MultiLegStrategyDefinition:
    return MultiLegStrategyDefinition(
        name="bear_put_spread",
        legs=(
            _single_leg(
                label="long_put",
                leg_kind=LegKind.PUT,
                direction=LegDirection.BUY,
                group="long_leg",
            ),
            _single_leg(
                label="short_put",
                leg_kind=LegKind.PUT,
                direction=LegDirection.SELL,
                group="short_leg",
            ),
        ),
    )


def _iron_condor() -> MultiLegStrategyDefinition:
    return MultiLegStrategyDefinition(
        name="iron_condor",
        legs=(
            _single_leg(
                label="long_put_wing",
                leg_kind=LegKind.PUT,
                direction=LegDirection.BUY,
                group="put_side",
            ),
            _single_leg(
                label="short_put",
                leg_kind=LegKind.PUT,
                direction=LegDirection.SELL,
                group="put_side",
            ),
            _single_leg(
                label="short_call",
                leg_kind=LegKind.CALL,
                direction=LegDirection.SELL,
                group="call_side",
            ),
            _single_leg(
                label="long_call_wing",
                leg_kind=LegKind.CALL,
                direction=LegDirection.BUY,
                group="call_side",
            ),
        ),
    )


def _iron_butterfly() -> MultiLegStrategyDefinition:
    return MultiLegStrategyDefinition(
        name="iron_butterfly",
        legs=(
            _single_leg(
                label="long_put_wing",
                leg_kind=LegKind.PUT,
                direction=LegDirection.BUY,
                group="put_side",
            ),
            _single_leg(
                label="short_put_atm",
                leg_kind=LegKind.PUT,
                direction=LegDirection.SELL,
                group="body",
            ),
            _single_leg(
                label="short_call_atm",
                leg_kind=LegKind.CALL,
                direction=LegDirection.SELL,
                group="body",
            ),
            _single_leg(
                label="long_call_wing",
                leg_kind=LegKind.CALL,
                direction=LegDirection.BUY,
                group="call_side",
            ),
        ),
    )


def _calendar_spread() -> MultiLegStrategyDefinition:
    return MultiLegStrategyDefinition(
        name="calendar_spread",
        legs=(
            _single_leg(
                label="short_front",
                leg_kind=LegKind.CALL,
                direction=LegDirection.SELL,
                group="front",
            ),
            _single_leg(
                label="long_back",
                leg_kind=LegKind.CALL,
                direction=LegDirection.BUY,
                group="back",
            ),
        ),
    )


def _diagonal_spread() -> MultiLegStrategyDefinition:
    return MultiLegStrategyDefinition(
        name="diagonal_spread",
        legs=(
            _single_leg(
                label="short_front_otm",
                leg_kind=LegKind.CALL,
                direction=LegDirection.SELL,
                group="front",
            ),
            _single_leg(
                label="long_back_itm",
                leg_kind=LegKind.CALL,
                direction=LegDirection.BUY,
                group="back",
            ),
        ),
    )


def _double_calendar() -> MultiLegStrategyDefinition:
    return MultiLegStrategyDefinition(
        name="double_calendar",
        legs=(
            _single_leg(
                label="short_front_put",
                leg_kind=LegKind.PUT,
                direction=LegDirection.SELL,
                group="put_front",
            ),
            _single_leg(
                label="long_back_put",
                leg_kind=LegKind.PUT,
                direction=LegDirection.BUY,
                group="put_back",
            ),
            _single_leg(
                label="short_front_call",
                leg_kind=LegKind.CALL,
                direction=LegDirection.SELL,
                group="call_front",
            ),
            _single_leg(
                label="long_back_call",
                leg_kind=LegKind.CALL,
                direction=LegDirection.BUY,
                group="call_back",
            ),
        ),
    )


def _double_diagonal() -> MultiLegStrategyDefinition:
    return MultiLegStrategyDefinition(
        name="double_diagonal",
        legs=(
            _single_leg(
                label="short_front_put",
                leg_kind=LegKind.PUT,
                direction=LegDirection.SELL,
                group="put_front",
            ),
            _single_leg(
                label="long_back_put",
                leg_kind=LegKind.PUT,
                direction=LegDirection.BUY,
                group="put_back",
            ),
            _single_leg(
                label="short_front_call",
                leg_kind=LegKind.CALL,
                direction=LegDirection.SELL,
                group="call_front",
            ),
            _single_leg(
                label="long_back_call",
                leg_kind=LegKind.CALL,
                direction=LegDirection.BUY,
                group="call_back",
            ),
        ),
    )


def _straddle() -> MultiLegStrategyDefinition:
    return MultiLegStrategyDefinition(
        name="straddle",
        legs=(
            _single_leg(
                label="call_atm",
                leg_kind=LegKind.CALL,
                direction=LegDirection.SELL,
                group="body",
            ),
            _single_leg(
                label="put_atm",
                leg_kind=LegKind.PUT,
                direction=LegDirection.SELL,
                group="body",
            ),
        ),
    )


def _strangle() -> MultiLegStrategyDefinition:
    return MultiLegStrategyDefinition(
        name="strangle",
        legs=(
            _single_leg(
                label="call_otm",
                leg_kind=LegKind.CALL,
                direction=LegDirection.SELL,
                group="body",
            ),
            _single_leg(
                label="put_otm",
                leg_kind=LegKind.PUT,
                direction=LegDirection.SELL,
                group="body",
            ),
        ),
    )


def _jade_lizard() -> MultiLegStrategyDefinition:
    return MultiLegStrategyDefinition(
        name="jade_lizard",
        legs=(
            _single_leg(
                label="short_put",
                leg_kind=LegKind.PUT,
                direction=LegDirection.SELL,
                group="put_side",
            ),
            _single_leg(
                label="short_call",
                leg_kind=LegKind.CALL,
                direction=LegDirection.SELL,
                group="call_spread",
            ),
            _single_leg(
                label="long_call_wing",
                leg_kind=LegKind.CALL,
                direction=LegDirection.BUY,
                group="call_spread",
            ),
        ),
    )


def _ratio_spread() -> MultiLegStrategyDefinition:
    return MultiLegStrategyDefinition(
        name="ratio_spread",
        legs=(
            MultiLegDefinitionLeg(
                label="long_call",
                leg_kind=LegKind.CALL,
                direction=LegDirection.BUY,
                effect=LegEffect.OPEN,
                quantity_ratio=1,
                contract_multiplier=100,
                leg_group="ratio",
            ),
            MultiLegDefinitionLeg(
                label="short_calls",
                leg_kind=LegKind.CALL,
                direction=LegDirection.SELL,
                effect=LegEffect.OPEN,
                quantity_ratio=2,
                contract_multiplier=100,
                leg_group="ratio",
            ),
        ),
    )


def _pmcc() -> MultiLegStrategyDefinition:
    return MultiLegStrategyDefinition(
        name="pmcc",
        legs=(
            _single_leg(
                label="long_deep_itm_call",
                leg_kind=LegKind.CALL,
                direction=LegDirection.BUY,
                group="replacement",
            ),
            _single_leg(
                label="short_otm_call",
                leg_kind=LegKind.CALL,
                direction=LegDirection.SELL,
                group="income",
            ),
        ),
        metadata={"pmcc_ready": True, "supports_long_call_replacement": True},
    )


def _synthetic_covered_call() -> MultiLegStrategyDefinition:
    return MultiLegStrategyDefinition(
        name="synthetic_covered_call",
        legs=(
            _single_leg(
                label="long_deep_itm_call",
                leg_kind=LegKind.CALL,
                direction=LegDirection.BUY,
                group="synthetic_stock",
            ),
            _single_leg(
                label="short_otm_call",
                leg_kind=LegKind.CALL,
                direction=LegDirection.SELL,
                group="income",
            ),
        ),
        metadata={
            "pmcc_like": True,
            "early_exercise_risk_metadata": True,
            "dividend_risk_metadata": True,
        },
    )


_LEGACY_TEMPLATE_BUILDERS: dict[str, Callable[[], MultiLegStrategyDefinition]] = {
    "covered_call": _covered_call,
    "cash_secured_put": _cash_secured_put,
    "bull_put_spread": _bull_put_spread,
    "bear_call_spread": _bear_call_spread,
    "bull_call_spread": _bull_call_spread,
    "bear_put_spread": _bear_put_spread,
    "iron_condor": _iron_condor,
    "iron_butterfly": _iron_butterfly,
    "calendar_spread": _calendar_spread,
    "diagonal_spread": _diagonal_spread,
    "double_calendar": _double_calendar,
    "double_diagonal": _double_diagonal,
    "straddle": _straddle,
    "strangle": _strangle,
    "jade_lizard": _jade_lizard,
    "ratio_spread": _ratio_spread,
    "pmcc": _pmcc,
    "synthetic_covered_call": _synthetic_covered_call,
}


_TEMPLATE_BUILDERS: dict[str, Callable[[], MultiLegStrategyDefinition]] = dict(
    _LEGACY_TEMPLATE_BUILDERS
)


STRATEGY_TEMPLATE_NAMES: tuple[str, ...] = tuple(sorted(_TEMPLATE_BUILDERS.keys()))


def _to_float(value: float | None) -> float:
    assert value is not None
    return float(value)


def _to_int(value: int | None) -> int:
    assert value is not None
    return int(value)
