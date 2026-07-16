"""Sprint 8A strategy library foundation for US-listed options research.

This module is deterministic and offline only. It defines strategy templates,
registry behavior, structural validation, payoff interfaces, risk
classification, serialization, and plugin extension hooks.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from hashlib import sha256
from math import inf
from statistics import mean
from typing import Any

from backend.pricing.models import ExerciseStyle, OptionType, SettlementType

from .strategies import (
    LegDirection,
    LegEffect,
    LegKind,
    MultiLegDefinitionLeg,
    MultiLegStrategyDefinition,
)


class StrategyLibraryError(RuntimeError):
    """Raised when strategy library operations fail."""


class StrategyFamily(StrEnum):
    DIRECTIONAL = "directional"
    VERTICAL = "vertical"
    IRON = "iron"
    BUTTERFLY_CONDOR = "butterfly_condor"
    VOLATILITY = "volatility"
    CALENDAR_DIAGONAL = "calendar_diagonal"
    COVERED_REPLACEMENT = "covered_replacement"
    RATIO_BACKSPREAD = "ratio_backspread"
    LIZARD_VARIANTS = "lizard_variants"
    BOX_ARBITRAGE = "box_arbitrage"
    CUSTOM = "custom"


class AccountType(StrEnum):
    CASH = "cash"
    MARGIN = "margin"
    PORTFOLIO_MARGIN = "portfolio_margin"


class UnderlyingSupport(StrEnum):
    EQUITY = "equity"
    ETF = "etf"
    INDEX = "index"
    FUTURES = "futures"


class StrategyBias(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    VARIABLE = "variable"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNBOUNDED = "unbounded"


class ValidationSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class ValidationCode(StrEnum):
    MISSING_LEGS = "missing_legs"
    DUPLICATE_LEGS = "duplicate_legs"
    INVALID_QUANTITY = "invalid_quantity"
    INVALID_STRIKE_ORDER = "invalid_strike_order"
    INVALID_EXPIRATION_ORDER = "invalid_expiration_order"
    MIXED_UNDERLYINGS = "mixed_underlyings"
    MIXED_MULTIPLIERS = "mixed_multipliers"
    INCOMPATIBLE_SETTLEMENT = "incompatible_settlement"
    UNSUPPORTED_EXERCISE_STYLE = "unsupported_exercise_style"
    UNDEFINED_RISK = "undefined_risk"
    UNCOVERED_RISK = "uncovered_risk"
    BROKEN_SPREAD = "broken_spread"
    INCOMPLETE_DATA = "incomplete_data"
    AMBIGUOUS_PAYOFF = "ambiguous_payoff"
    UNSUPPORTED_CONTRACT_ADJUSTMENTS = "unsupported_contract_adjustments"
    PARTIAL_FILL_BREAKAGE = "partial_fill_breakage"


class PayoffTag(StrEnum):
    CREDIT = "credit"
    DEBIT = "debit"
    EVEN = "even"


@dataclass(slots=True, frozen=True)
class StrategyTemplateLeg:
    label: str
    leg_kind: LegKind
    direction: LegDirection
    quantity_ratio: int = 1
    contract_multiplier: int = 100
    option_type_requirement: OptionType | None = None
    strike_order_hint: str | None = None
    expiration_order_hint: str | None = None
    exercise_style_requirement: ExerciseStyle | None = None
    settlement_requirement: SettlementType | None = None
    leg_group: str | None = None
    required: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class EntryRequirements:
    required_data: tuple[str, ...] = ()
    liquidity_threshold: float | None = None
    bid_ask_width_threshold: float | None = None
    iv_rank_threshold: float | None = None
    iv_percentile_threshold: float | None = None
    quality_score_threshold: float | None = None
    earnings_timing: str | None = None
    event_restrictions: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class CompatibilityRules:
    supported_underlyings: tuple[UnderlyingSupport, ...]
    supported_exercise_styles: tuple[ExerciseStyle, ...]
    supported_settlement_styles: tuple[SettlementType, ...]
    supported_account_types: tuple[AccountType, ...]
    supported_lifecycle_policies: tuple[str, ...]
    supported_roll_policies: tuple[str, ...]
    supports_adjusted_contracts: bool = False


@dataclass(slots=True, frozen=True)
class RiskClassification:
    directional_bias: StrategyBias
    volatility_bias: StrategyBias
    theta_bias: StrategyBias
    gamma_bias: StrategyBias
    vega_bias: StrategyBias
    event_sensitivity: RiskLevel
    assignment_sensitivity: RiskLevel
    dividend_sensitivity: RiskLevel
    margin_complexity: RiskLevel
    liquidity_sensitivity: RiskLevel
    tail_risk: RiskLevel
    defined_risk: bool
    multi_expiry: bool
    has_stock_component: bool
    american_style_sensitivity: RiskLevel


@dataclass(slots=True, frozen=True)
class OptimizerParameterContract:
    delta_ranges: tuple[tuple[float, float], ...] = ()
    dte_ranges: tuple[tuple[int, int], ...] = ()
    width_ranges: tuple[tuple[float, float], ...] = ()
    ratio_choices: tuple[tuple[int, ...], ...] = ()
    strike_selection_modes: tuple[str, ...] = ()
    term_structure_filters: tuple[str, ...] = ()
    iv_rank_filters: tuple[tuple[float, float], ...] = ()
    iv_percentile_filters: tuple[tuple[float, float], ...] = ()
    historical_volatility_filters: tuple[tuple[float, float], ...] = ()
    realized_volatility_filters: tuple[tuple[float, float], ...] = ()
    earnings_timing: tuple[str, ...] = ()
    quality_thresholds: tuple[float, ...] = ()
    liquidity_thresholds: tuple[float, ...] = ()
    capital_constraints: tuple[float, ...] = ()
    management_policy_compatibility: tuple[str, ...] = ()
    roll_policy_compatibility: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class TemplateDeprecation:
    is_deprecated: bool = False
    deprecated_after: date | None = None
    replacement_identifier: str | None = None
    reason: str | None = None


@dataclass(slots=True, frozen=True)
class StrategyTemplate:
    name: str
    canonical_identifier: str
    version: str
    aliases: tuple[str, ...]
    family: StrategyFamily
    legs: tuple[StrategyTemplateLeg, ...]
    entry_requirements: EntryRequirements
    compatibility: CompatibilityRules
    risk_classification: RiskClassification
    optimizer_contract: OptimizerParameterContract
    known_limitations: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    deprecation: TemplateDeprecation = field(default_factory=TemplateDeprecation)

    def compile_generic_definition(
        self,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> MultiLegStrategyDefinition:
        merged = dict(self.metadata)
        if metadata:
            merged.update(metadata)
        merged["canonical_identifier"] = self.canonical_identifier
        merged["template_version"] = self.version
        merged["strategy_family"] = self.family.value

        generic_legs = tuple(
            MultiLegDefinitionLeg(
                label=leg.label,
                leg_kind=leg.leg_kind,
                direction=leg.direction,
                effect=LegEffect.OPEN,
                quantity_ratio=leg.quantity_ratio,
                contract_multiplier=leg.contract_multiplier,
                strike_policy=None,
                expiration_policy=None,
                delta_policy=None,
                moneyness_policy=None,
                dte_policy=None,
                exercise_style_requirement=(
                    None
                    if leg.exercise_style_requirement is None
                    else leg.exercise_style_requirement.value
                ),
                settlement_requirement=(
                    None if leg.settlement_requirement is None else leg.settlement_requirement.value
                ),
                leg_group=leg.leg_group,
                metadata=dict(leg.metadata),
            )
            for leg in self.legs
        )
        validation_rules: tuple[dict[str, Any], ...] = (
            {
                "rule": "required_legs",
                "count": len([leg for leg in self.legs if leg.required]),
            },
            {
                "rule": "supported_exercise_styles",
                "styles": tuple(
                    style.value for style in self.compatibility.supported_exercise_styles
                ),
            },
            {
                "rule": "supported_settlement_styles",
                "styles": tuple(
                    style.value for style in self.compatibility.supported_settlement_styles
                ),
            },
        )
        return MultiLegStrategyDefinition(
            name=self.name,
            legs=generic_legs,
            validation_rules=validation_rules,
            metadata=merged,
        )


@dataclass(slots=True, frozen=True)
class CommonStrategyParameters:
    symbol: str
    valuation_timestamp: datetime
    quantity: int = 1
    long_or_short_bias: str | None = None
    target_delta: float | None = None
    target_strike: float | None = None
    strike_width: float | None = None
    inner_width: float | None = None
    wing_width: float | None = None
    front_dte: int | None = None
    back_dte: int | None = None
    long_dte: int | None = None
    short_dte: int | None = None
    expiration_preference: str | None = None
    call_or_put_selection: str | None = None
    exercise_style_requirement: ExerciseStyle | None = None
    settlement_requirement: SettlementType | None = None
    target_premium: float | None = None
    target_credit: float | None = None
    maximum_debit: float | None = None
    minimum_credit: float | None = None
    liquidity_threshold: float | None = None
    bid_ask_width_threshold: float | None = None
    iv_rank_threshold: float | None = None
    iv_percentile_threshold: float | None = None
    historical_volatility_threshold: float | None = None
    realized_volatility_threshold: float | None = None
    term_structure_regime: str | None = None
    contango_or_backwardation_threshold: float | None = None
    skew_threshold: float | None = None
    earnings_timing: str | None = None
    event_restrictions: tuple[str, ...] = ()
    quality_score_threshold: float | None = None
    capital_limit: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class StrategySelectedLeg:
    label: str
    leg_kind: LegKind
    direction: LegDirection
    quantity: int
    strike: float | None
    expiration: date | None
    option_type: OptionType | None
    premium: float | None
    underlying: str
    exercise_style: ExerciseStyle | None
    settlement_style: SettlementType | None
    multiplier: int
    deliverable: str | None = None
    currency: str = "USD"
    adjusted_contract: bool = False
    liquidity_score: float | None = None
    quote_quality: float | None = None
    dte: int | None = None
    delta: float | None = None
    earnings_placement: str | None = None
    dividend_proximity_days: int | None = None
    implied_volatility: float | None = None


@dataclass(slots=True, frozen=True)
class StrategyValidationIssue:
    code: ValidationCode
    severity: ValidationSeverity
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class StrategyStructuralValidationResult:
    errors: tuple[StrategyValidationIssue, ...]
    warnings: tuple[StrategyValidationIssue, ...]

    @property
    def is_valid(self) -> bool:
        return not self.errors


@dataclass(slots=True, frozen=True)
class PayoffPoint:
    underlying_price: float
    payoff: float


@dataclass(slots=True, frozen=True)
class StrategyPayoffSummary:
    points: tuple[PayoffPoint, ...]
    maximum_profit: float | None
    maximum_loss: float | None
    breakevens: tuple[float, ...]
    defined_risk: bool
    capital_at_risk: float | None
    credit_or_debit: PayoffTag
    intrinsic_value: float | None
    extrinsic_value: float | None
    slope_regions: tuple[str, ...]
    discontinuities: tuple[float, ...]
    residual_exposure: dict[str, float]
    assignment_sensitive: bool
    dividend_sensitive: bool
    warnings: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class StrategyTemplateCatalogueItem:
    canonical_identifier: str
    name: str
    version: str
    family: StrategyFamily
    aliases: tuple[str, ...]
    deprecated: bool


@dataclass(slots=True, frozen=True)
class StrategyTemplatePluginMetadata:
    plugin_name: str
    plugin_version: str
    api_version: str
    namespace: str
    allow_overrides: bool = False


@dataclass(slots=True, frozen=True)
class CustomStrategyDefinition:
    strategy_id: str
    display_name: str
    legs: tuple[StrategyTemplateLeg, ...]
    leg_groups: dict[str, tuple[str, ...]] = field(default_factory=dict)
    dependency_graph: dict[str, tuple[str, ...]] = field(default_factory=dict)
    per_leg_selection_rules: dict[str, dict[str, Any]] = field(default_factory=dict)
    per_leg_lifecycle_metadata: dict[str, dict[str, Any]] = field(default_factory=dict)
    custom_validation: tuple[dict[str, Any], ...] = ()
    custom_payoff_classification: dict[str, Any] = field(default_factory=dict)
    custom_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StrategyTemplateRegistry:
    _templates: dict[str, StrategyTemplate] = field(default_factory=dict)
    _aliases: dict[str, str] = field(default_factory=dict)
    _plugin_origins: dict[str, StrategyTemplatePluginMetadata] = field(default_factory=dict)

    def register(self, template: StrategyTemplate) -> None:
        identifier = template.canonical_identifier
        if identifier in self._templates:
            raise StrategyLibraryError(f"template identifier already registered: {identifier}")
        self._templates[identifier] = template
        for alias in template.aliases:
            if alias in self._aliases and self._aliases[alias] != identifier:
                raise StrategyLibraryError(f"template alias collision: {alias}")
            self._aliases[alias] = identifier

    def register_plugin_templates(
        self,
        *,
        metadata: StrategyTemplatePluginMetadata,
        templates: tuple[StrategyTemplate, ...],
    ) -> None:
        if metadata.api_version != "8A-v1":
            raise StrategyLibraryError("incompatible plugin API version")
        for template in templates:
            identifier = template.canonical_identifier
            existing = self._templates.get(identifier)
            if existing is not None and not metadata.allow_overrides:
                raise StrategyLibraryError(
                    f"plugin template collision without override enabled: {identifier}"
                )
            if existing is not None and metadata.allow_overrides:
                self._templates[identifier] = template
            else:
                self.register(template)
            self._plugin_origins[identifier] = metadata

    def resolve(self, name_or_alias: str) -> StrategyTemplate:
        if name_or_alias in self._templates:
            return self._templates[name_or_alias]
        identifier = self._aliases.get(name_or_alias)
        if identifier is None:
            raise StrategyLibraryError(f"unknown strategy template: {name_or_alias}")
        return self._templates[identifier]

    def discover(
        self,
        *,
        include_deprecated: bool = False,
        family: StrategyFamily | None = None,
    ) -> tuple[StrategyTemplateCatalogueItem, ...]:
        items = []
        for template in sorted(
            self._templates.values(), key=lambda item: item.canonical_identifier
        ):
            if family is not None and template.family is not family:
                continue
            if template.deprecation.is_deprecated and not include_deprecated:
                continue
            items.append(
                StrategyTemplateCatalogueItem(
                    canonical_identifier=template.canonical_identifier,
                    name=template.name,
                    version=template.version,
                    family=template.family,
                    aliases=template.aliases,
                    deprecated=template.deprecation.is_deprecated,
                )
            )
        return tuple(items)

    def deprecated_templates(self) -> tuple[StrategyTemplate, ...]:
        return tuple(
            template for template in self._templates.values() if template.deprecation.is_deprecated
        )

    def versions(self, canonical_identifier: str) -> tuple[str, ...]:
        template = self.resolve(canonical_identifier)
        versions = [template.version]
        if template.deprecation.replacement_identifier is not None:
            replacement = self.resolve(template.deprecation.replacement_identifier)
            versions.append(replacement.version)
        return tuple(sorted(set(versions)))

    def plugin_origin(self, canonical_identifier: str) -> StrategyTemplatePluginMetadata | None:
        return self._plugin_origins.get(canonical_identifier)


@dataclass(slots=True)
class StrategyStructureValidator:
    def validate(
        self,
        *,
        template: StrategyTemplate,
        selected_legs: tuple[StrategySelectedLeg, ...],
    ) -> StrategyStructuralValidationResult:
        errors: list[StrategyValidationIssue] = []
        warnings: list[StrategyValidationIssue] = []

        if not selected_legs:
            errors.append(
                StrategyValidationIssue(
                    code=ValidationCode.MISSING_LEGS,
                    severity=ValidationSeverity.ERROR,
                    message="strategy has no selected legs",
                )
            )
            return StrategyStructuralValidationResult(
                errors=tuple(errors), warnings=tuple(warnings)
            )

        labels = [leg.label for leg in selected_legs]
        if len(set(labels)) != len(labels):
            errors.append(
                StrategyValidationIssue(
                    code=ValidationCode.DUPLICATE_LEGS,
                    severity=ValidationSeverity.ERROR,
                    message="duplicate leg labels in selected strategy",
                )
            )

        if any(leg.quantity <= 0 for leg in selected_legs):
            errors.append(
                StrategyValidationIssue(
                    code=ValidationCode.INVALID_QUANTITY,
                    severity=ValidationSeverity.ERROR,
                    message="all selected legs require positive quantity",
                )
            )

        underlyings = {leg.underlying for leg in selected_legs}
        if len(underlyings) > 1:
            errors.append(
                StrategyValidationIssue(
                    code=ValidationCode.MIXED_UNDERLYINGS,
                    severity=ValidationSeverity.ERROR,
                    message="mixed underlyings are not supported in one strategy instance",
                    details={"underlyings": sorted(underlyings)},
                )
            )

        multipliers = {leg.multiplier for leg in selected_legs}
        if len(multipliers) > 1:
            errors.append(
                StrategyValidationIssue(
                    code=ValidationCode.MIXED_MULTIPLIERS,
                    severity=ValidationSeverity.ERROR,
                    message="mixed multipliers are not supported",
                    details={"multipliers": sorted(multipliers)},
                )
            )

        style_values = {
            leg.exercise_style for leg in selected_legs if leg.exercise_style is not None
        }
        unsupported_styles = [
            style
            for style in style_values
            if style not in template.compatibility.supported_exercise_styles
        ]
        if unsupported_styles:
            errors.append(
                StrategyValidationIssue(
                    code=ValidationCode.UNSUPPORTED_EXERCISE_STYLE,
                    severity=ValidationSeverity.ERROR,
                    message="selected legs include unsupported exercise style",
                    details={"styles": [item.value for item in unsupported_styles]},
                )
            )

        settlement_values = {
            leg.settlement_style for leg in selected_legs if leg.settlement_style is not None
        }
        unsupported_settlement = [
            style
            for style in settlement_values
            if style not in template.compatibility.supported_settlement_styles
        ]
        if unsupported_settlement:
            errors.append(
                StrategyValidationIssue(
                    code=ValidationCode.INCOMPATIBLE_SETTLEMENT,
                    severity=ValidationSeverity.ERROR,
                    message="selected legs include incompatible settlement style",
                    details={"styles": [item.value for item in unsupported_settlement]},
                )
            )

        if (
            any(leg.adjusted_contract for leg in selected_legs)
            and not template.compatibility.supports_adjusted_contracts
        ):
            warnings.append(
                StrategyValidationIssue(
                    code=ValidationCode.UNSUPPORTED_CONTRACT_ADJUSTMENTS,
                    severity=ValidationSeverity.WARNING,
                    message="template does not claim support for adjusted contracts",
                )
            )

        if _has_strike_ordering_issue(template=template, selected_legs=selected_legs):
            errors.append(
                StrategyValidationIssue(
                    code=ValidationCode.INVALID_STRIKE_ORDER,
                    severity=ValidationSeverity.ERROR,
                    message="strike ordering violates template structure",
                )
            )

        if _has_expiration_ordering_issue(template=template, selected_legs=selected_legs):
            errors.append(
                StrategyValidationIssue(
                    code=ValidationCode.INVALID_EXPIRATION_ORDER,
                    severity=ValidationSeverity.ERROR,
                    message="expiration ordering violates template structure",
                )
            )

        if any(leg.liquidity_score is None or leg.quote_quality is None for leg in selected_legs):
            warnings.append(
                StrategyValidationIssue(
                    code=ValidationCode.INCOMPLETE_DATA,
                    severity=ValidationSeverity.WARNING,
                    message="liquidity or quote-quality data missing for one or more legs",
                )
            )

        if not template.risk_classification.defined_risk:
            warnings.append(
                StrategyValidationIssue(
                    code=ValidationCode.UNDEFINED_RISK,
                    severity=ValidationSeverity.WARNING,
                    message="strategy has undefined risk profile",
                )
            )

        return StrategyStructuralValidationResult(errors=tuple(errors), warnings=tuple(warnings))


@dataclass(slots=True)
class StrategyPayoffAnalyzer:
    def summarize(
        self,
        *,
        template: StrategyTemplate,
        selected_legs: tuple[StrategySelectedLeg, ...],
        price_grid: tuple[float, ...],
    ) -> StrategyPayoffSummary:
        if not selected_legs:
            return StrategyPayoffSummary(
                points=(),
                maximum_profit=None,
                maximum_loss=None,
                breakevens=(),
                defined_risk=False,
                capital_at_risk=None,
                credit_or_debit=PayoffTag.EVEN,
                intrinsic_value=None,
                extrinsic_value=None,
                slope_regions=(),
                discontinuities=(),
                residual_exposure={},
                assignment_sensitive=False,
                dividend_sensitive=False,
                warnings=("no_legs_selected",),
            )

        warnings: list[str] = []
        if any(
            leg.premium is None
            for leg in selected_legs
            if leg.leg_kind in {LegKind.CALL, LegKind.PUT}
        ):
            warnings.append("missing_option_premium_data")
        if any(
            leg.strike is None
            for leg in selected_legs
            if leg.leg_kind in {LegKind.CALL, LegKind.PUT}
        ):
            warnings.append("missing_option_strike_data")

        points: list[PayoffPoint] = []
        for price in sorted(price_grid):
            points.append(
                PayoffPoint(
                    underlying_price=price, payoff=round(_payoff_at_price(selected_legs, price), 8)
                )
            )

        payoffs = [point.payoff for point in points]
        max_profit = max(payoffs) if payoffs else None
        max_loss = min(payoffs) if payoffs else None
        if max_profit is not None and max_profit > 1e9:
            max_profit = inf
        if max_loss is not None and max_loss < -1e9:
            max_loss = -inf

        breakevens = _breakeven_points(points)
        discontinuities = tuple(
            sorted(
                {
                    leg.strike
                    for leg in selected_legs
                    if leg.strike is not None and leg.leg_kind in {LegKind.CALL, LegKind.PUT}
                }
            )
        )
        residual = {
            "delta_proxy": round(mean([leg.delta or 0.0 for leg in selected_legs]), 8),
            "vega_proxy": round(mean([leg.implied_volatility or 0.0 for leg in selected_legs]), 8),
        }

        intrinsic = _intrinsic_total(selected_legs)
        extrinsic = _extrinsic_total(selected_legs)
        if intrinsic is None or extrinsic is None:
            warnings.append("intrinsic_extrinsic_unavailable")

        return StrategyPayoffSummary(
            points=tuple(points),
            maximum_profit=None
            if not points
            else (None if inf in {max_profit, -inf} else max_profit),
            maximum_loss=None if not points else (None if inf in {max_profit, -inf} else max_loss),
            breakevens=breakevens,
            defined_risk=template.risk_classification.defined_risk,
            capital_at_risk=None if max_loss is None else abs(min(0.0, max_loss)),
            credit_or_debit=_credit_or_debit(selected_legs),
            intrinsic_value=intrinsic,
            extrinsic_value=extrinsic,
            slope_regions=_slope_regions(points),
            discontinuities=discontinuities,
            residual_exposure=residual,
            assignment_sensitive=template.risk_classification.assignment_sensitivity
            in {
                RiskLevel.MEDIUM,
                RiskLevel.HIGH,
                RiskLevel.UNBOUNDED,
            },
            dividend_sensitive=template.risk_classification.dividend_sensitivity
            in {
                RiskLevel.MEDIUM,
                RiskLevel.HIGH,
                RiskLevel.UNBOUNDED,
            },
            warnings=tuple(warnings),
        )


def serialize_template(template: StrategyTemplate) -> dict[str, Any]:
    payload = asdict(template)
    payload["schema_version"] = "strategy-template-schema-v1"
    return payload


def load_template(payload: dict[str, Any]) -> StrategyTemplate:
    schema_version = payload.get("schema_version", "strategy-template-schema-v1")
    if schema_version != "strategy-template-schema-v1":
        raise StrategyLibraryError(f"unsupported schema version: {schema_version}")

    compatibility = payload["compatibility"]
    risk = payload["risk_classification"]
    optimizer = payload["optimizer_contract"]
    deprecation_payload = payload.get("deprecation", {})

    return StrategyTemplate(
        name=payload["name"],
        canonical_identifier=payload["canonical_identifier"],
        version=payload["version"],
        aliases=tuple(payload.get("aliases", ())),
        family=StrategyFamily(payload["family"]),
        legs=tuple(
            StrategyTemplateLeg(
                label=leg["label"],
                leg_kind=LegKind(leg["leg_kind"]),
                direction=LegDirection(leg["direction"]),
                quantity_ratio=int(leg.get("quantity_ratio", 1)),
                contract_multiplier=int(leg.get("contract_multiplier", 100)),
                option_type_requirement=(
                    None
                    if leg.get("option_type_requirement") is None
                    else OptionType(leg["option_type_requirement"])
                ),
                strike_order_hint=leg.get("strike_order_hint"),
                expiration_order_hint=leg.get("expiration_order_hint"),
                exercise_style_requirement=(
                    None
                    if leg.get("exercise_style_requirement") is None
                    else ExerciseStyle(leg["exercise_style_requirement"])
                ),
                settlement_requirement=(
                    None
                    if leg.get("settlement_requirement") is None
                    else SettlementType(leg["settlement_requirement"])
                ),
                leg_group=leg.get("leg_group"),
                required=bool(leg.get("required", True)),
                metadata=dict(leg.get("metadata", {})),
            )
            for leg in payload["legs"]
        ),
        entry_requirements=EntryRequirements(**payload.get("entry_requirements", {})),
        compatibility=CompatibilityRules(
            supported_underlyings=tuple(
                UnderlyingSupport(item) for item in compatibility["supported_underlyings"]
            ),
            supported_exercise_styles=tuple(
                ExerciseStyle(item) for item in compatibility["supported_exercise_styles"]
            ),
            supported_settlement_styles=tuple(
                SettlementType(item) for item in compatibility["supported_settlement_styles"]
            ),
            supported_account_types=tuple(
                AccountType(item) for item in compatibility["supported_account_types"]
            ),
            supported_lifecycle_policies=tuple(compatibility["supported_lifecycle_policies"]),
            supported_roll_policies=tuple(compatibility["supported_roll_policies"]),
            supports_adjusted_contracts=bool(
                compatibility.get("supports_adjusted_contracts", False)
            ),
        ),
        risk_classification=RiskClassification(
            directional_bias=StrategyBias(risk["directional_bias"]),
            volatility_bias=StrategyBias(risk["volatility_bias"]),
            theta_bias=StrategyBias(risk["theta_bias"]),
            gamma_bias=StrategyBias(risk["gamma_bias"]),
            vega_bias=StrategyBias(risk["vega_bias"]),
            event_sensitivity=RiskLevel(risk["event_sensitivity"]),
            assignment_sensitivity=RiskLevel(risk["assignment_sensitivity"]),
            dividend_sensitivity=RiskLevel(risk["dividend_sensitivity"]),
            margin_complexity=RiskLevel(risk["margin_complexity"]),
            liquidity_sensitivity=RiskLevel(risk["liquidity_sensitivity"]),
            tail_risk=RiskLevel(risk["tail_risk"]),
            defined_risk=bool(risk["defined_risk"]),
            multi_expiry=bool(risk["multi_expiry"]),
            has_stock_component=bool(risk["has_stock_component"]),
            american_style_sensitivity=RiskLevel(risk["american_style_sensitivity"]),
        ),
        optimizer_contract=OptimizerParameterContract(**optimizer),
        known_limitations=tuple(payload.get("known_limitations", ())),
        metadata=dict(payload.get("metadata", {})),
        deprecation=TemplateDeprecation(
            is_deprecated=bool(deprecation_payload.get("is_deprecated", False)),
            deprecated_after=deprecation_payload.get("deprecated_after"),
            replacement_identifier=deprecation_payload.get("replacement_identifier"),
            reason=deprecation_payload.get("reason"),
        ),
    )


def deterministic_strategy_library_checksum(*, templates: tuple[StrategyTemplate, ...]) -> str:
    normalized = []
    for template in sorted(templates, key=lambda item: item.canonical_identifier):
        normalized.append(
            {
                "canonical_identifier": template.canonical_identifier,
                "version": template.version,
                "aliases": tuple(sorted(template.aliases)),
                "family": template.family.value,
                "legs": tuple(
                    (
                        leg.label,
                        leg.leg_kind.value,
                        leg.direction.value,
                        leg.quantity_ratio,
                    )
                    for leg in template.legs
                ),
            }
        )
    payload = {
        "schema": "strategy-library-checksum-v1",
        "items": normalized,
    }
    return sha256(repr(payload).encode("utf-8")).hexdigest()


def default_strategy_template_registry() -> StrategyTemplateRegistry:
    registry = StrategyTemplateRegistry()
    for template in _default_templates():
        registry.register(template)
    return registry


def compile_strategy_template(
    *,
    template_name: str,
    metadata: dict[str, Any] | None = None,
    registry: StrategyTemplateRegistry | None = None,
) -> MultiLegStrategyDefinition:
    source = registry or default_strategy_template_registry()
    template = source.resolve(template_name)
    return template.compile_generic_definition(metadata=metadata)


def classify_strategy_risk(
    *, template_name: str, registry: StrategyTemplateRegistry | None = None
) -> RiskClassification:
    source = registry or default_strategy_template_registry()
    return source.resolve(template_name).risk_classification


def strategy_optimizer_contract(
    *,
    template_name: str,
    registry: StrategyTemplateRegistry | None = None,
) -> OptimizerParameterContract:
    source = registry or default_strategy_template_registry()
    return source.resolve(template_name).optimizer_contract


def strategy_template_api_payload(
    *,
    template_name: str,
    registry: StrategyTemplateRegistry | None = None,
) -> dict[str, Any]:
    source = registry or default_strategy_template_registry()
    template = source.resolve(template_name)
    payload = serialize_template(template)
    payload["generated_at"] = datetime.now(tz=UTC).isoformat()
    return payload


def _default_templates() -> tuple[StrategyTemplate, ...]:
    common_compat = CompatibilityRules(
        supported_underlyings=(
            UnderlyingSupport.EQUITY,
            UnderlyingSupport.ETF,
            UnderlyingSupport.INDEX,
        ),
        supported_exercise_styles=(ExerciseStyle.AMERICAN, ExerciseStyle.EUROPEAN),
        supported_settlement_styles=(SettlementType.PHYSICAL, SettlementType.CASH),
        supported_account_types=(
            AccountType.CASH,
            AccountType.MARGIN,
            AccountType.PORTFOLIO_MARGIN,
        ),
        supported_lifecycle_policies=("profit_target", "stop_loss", "time_exit", "volatility_exit"),
        supported_roll_policies=("time_roll", "delta_roll", "theta_roll", "event_roll"),
        supports_adjusted_contracts=False,
    )

    directional_bounded = RiskClassification(
        directional_bias=StrategyBias.VARIABLE,
        volatility_bias=StrategyBias.VARIABLE,
        theta_bias=StrategyBias.VARIABLE,
        gamma_bias=StrategyBias.VARIABLE,
        vega_bias=StrategyBias.VARIABLE,
        event_sensitivity=RiskLevel.MEDIUM,
        assignment_sensitivity=RiskLevel.MEDIUM,
        dividend_sensitivity=RiskLevel.MEDIUM,
        margin_complexity=RiskLevel.MEDIUM,
        liquidity_sensitivity=RiskLevel.MEDIUM,
        tail_risk=RiskLevel.MEDIUM,
        defined_risk=True,
        multi_expiry=False,
        has_stock_component=False,
        american_style_sensitivity=RiskLevel.MEDIUM,
    )

    unbounded_risk = RiskClassification(
        directional_bias=StrategyBias.VARIABLE,
        volatility_bias=StrategyBias.VARIABLE,
        theta_bias=StrategyBias.VARIABLE,
        gamma_bias=StrategyBias.VARIABLE,
        vega_bias=StrategyBias.VARIABLE,
        event_sensitivity=RiskLevel.HIGH,
        assignment_sensitivity=RiskLevel.HIGH,
        dividend_sensitivity=RiskLevel.HIGH,
        margin_complexity=RiskLevel.HIGH,
        liquidity_sensitivity=RiskLevel.HIGH,
        tail_risk=RiskLevel.UNBOUNDED,
        defined_risk=False,
        multi_expiry=False,
        has_stock_component=False,
        american_style_sensitivity=RiskLevel.HIGH,
    )

    calendar_risk = RiskClassification(
        directional_bias=StrategyBias.VARIABLE,
        volatility_bias=StrategyBias.BULLISH,
        theta_bias=StrategyBias.BULLISH,
        gamma_bias=StrategyBias.BEARISH,
        vega_bias=StrategyBias.BULLISH,
        event_sensitivity=RiskLevel.HIGH,
        assignment_sensitivity=RiskLevel.HIGH,
        dividend_sensitivity=RiskLevel.HIGH,
        margin_complexity=RiskLevel.MEDIUM,
        liquidity_sensitivity=RiskLevel.MEDIUM,
        tail_risk=RiskLevel.MEDIUM,
        defined_risk=True,
        multi_expiry=True,
        has_stock_component=False,
        american_style_sensitivity=RiskLevel.HIGH,
    )

    covered_risk = RiskClassification(
        directional_bias=StrategyBias.BULLISH,
        volatility_bias=StrategyBias.BEARISH,
        theta_bias=StrategyBias.BULLISH,
        gamma_bias=StrategyBias.BEARISH,
        vega_bias=StrategyBias.BEARISH,
        event_sensitivity=RiskLevel.MEDIUM,
        assignment_sensitivity=RiskLevel.HIGH,
        dividend_sensitivity=RiskLevel.HIGH,
        margin_complexity=RiskLevel.MEDIUM,
        liquidity_sensitivity=RiskLevel.MEDIUM,
        tail_risk=RiskLevel.HIGH,
        defined_risk=False,
        multi_expiry=False,
        has_stock_component=True,
        american_style_sensitivity=RiskLevel.HIGH,
    )

    optimizer = OptimizerParameterContract(
        delta_ranges=((0.1, 0.9),),
        dte_ranges=((7, 540),),
        width_ranges=((1.0, 50.0),),
        ratio_choices=((1, 1), (1, 2), (1, 3)),
        strike_selection_modes=("delta", "moneyness", "premium", "distance"),
        term_structure_filters=("contango", "backwardation", "flat"),
        iv_rank_filters=((0.0, 1.0),),
        iv_percentile_filters=((0.0, 1.0),),
        historical_volatility_filters=((0.0, 2.0),),
        realized_volatility_filters=((0.0, 2.0),),
        earnings_timing=("none", "pre", "post", "avoid"),
        quality_thresholds=(0.3, 0.5, 0.7),
        liquidity_thresholds=(0.3, 0.5, 0.7),
        capital_constraints=(500.0, 1000.0, 5000.0, 20000.0),
        management_policy_compatibility=("profit_target", "stop_loss", "time_exit"),
        roll_policy_compatibility=("time_roll", "delta_roll", "event_roll"),
    )

    templates = []

    def add(
        *,
        name: str,
        canonical_identifier: str,
        family: StrategyFamily,
        legs: tuple[StrategyTemplateLeg, ...],
        aliases: tuple[str, ...] = (),
        risk: RiskClassification = directional_bounded,
        limitations: tuple[str, ...] = (),
    ) -> None:
        templates.append(
            StrategyTemplate(
                name=name,
                canonical_identifier=canonical_identifier,
                version="8A-v1",
                aliases=aliases,
                family=family,
                legs=legs,
                entry_requirements=EntryRequirements(required_data=("quotes", "greeks", "iv")),
                compatibility=common_compat,
                risk_classification=risk,
                optimizer_contract=optimizer,
                known_limitations=limitations,
                metadata={
                    "analytics_readiness": {
                        "pop": True,
                        "expected_value": True,
                        "theta_capture": True,
                        "vega_exposure": True,
                        "gamma_exposure": True,
                        "drawdown": True,
                        "capital_efficiency": True,
                        "margin_usage": True,
                        "assignment_frequency": True,
                        "exercise_frequency": True,
                        "roll_frequency": True,
                        "performance_by_volatility_regime": True,
                        "performance_by_term_structure_regime": True,
                        "performance_around_earnings": True,
                        "performance_around_dividends": True,
                    }
                },
            )
        )

    def option_leg(
        label: str,
        option_type: OptionType,
        direction: LegDirection,
        *,
        group: str,
        ratio: int = 1,
        strike_hint: str | None = None,
        expiry_hint: str | None = None,
    ) -> StrategyTemplateLeg:
        return StrategyTemplateLeg(
            label=label,
            leg_kind=LegKind.CALL if option_type is OptionType.CALL else LegKind.PUT,
            direction=direction,
            quantity_ratio=ratio,
            option_type_requirement=option_type,
            strike_order_hint=strike_hint,
            expiration_order_hint=expiry_hint,
            leg_group=group,
        )

    def stock_leg(
        label: str, direction: LegDirection, *, ratio: int = 100, group: str = "stock"
    ) -> StrategyTemplateLeg:
        return StrategyTemplateLeg(
            label=label,
            leg_kind=LegKind.STOCK,
            direction=direction,
            quantity_ratio=ratio,
            contract_multiplier=1,
            leg_group=group,
        )

    def cash_leg(label: str, *, group: str = "cash") -> StrategyTemplateLeg:
        return StrategyTemplateLeg(
            label=label,
            leg_kind=LegKind.CASH,
            direction=LegDirection.BUY,
            quantity_ratio=1,
            contract_multiplier=1,
            leg_group=group,
        )

    # Core directional
    add(
        name="long_call",
        canonical_identifier="directional.long_call",
        family=StrategyFamily.DIRECTIONAL,
        legs=(option_leg("long_call", OptionType.CALL, LegDirection.BUY, group="directional"),),
        aliases=("buy_call",),
        risk=unbounded_risk,
    )
    add(
        name="long_put",
        canonical_identifier="directional.long_put",
        family=StrategyFamily.DIRECTIONAL,
        legs=(option_leg("long_put", OptionType.PUT, LegDirection.BUY, group="directional"),),
        aliases=("buy_put",),
        risk=directional_bounded,
    )
    add(
        name="short_call",
        canonical_identifier="directional.short_call",
        family=StrategyFamily.DIRECTIONAL,
        legs=(option_leg("short_call", OptionType.CALL, LegDirection.SELL, group="directional"),),
        aliases=("sell_call",),
        risk=unbounded_risk,
    )
    add(
        name="short_put",
        canonical_identifier="directional.short_put",
        family=StrategyFamily.DIRECTIONAL,
        legs=(option_leg("short_put", OptionType.PUT, LegDirection.SELL, group="directional"),),
        aliases=("sell_put",),
        risk=unbounded_risk,
    )
    add(
        name="covered_call",
        canonical_identifier="directional.covered_call",
        family=StrategyFamily.DIRECTIONAL,
        legs=(
            stock_leg("long_stock", LegDirection.BUY),
            option_leg("short_call", OptionType.CALL, LegDirection.SELL, group="income"),
        ),
        risk=covered_risk,
    )
    add(
        name="cash_secured_put",
        canonical_identifier="directional.cash_secured_put",
        family=StrategyFamily.DIRECTIONAL,
        legs=(
            cash_leg("cash_collateral"),
            option_leg("short_put", OptionType.PUT, LegDirection.SELL, group="income"),
        ),
        risk=directional_bounded,
    )
    add(
        name="protective_put",
        canonical_identifier="directional.protective_put",
        family=StrategyFamily.DIRECTIONAL,
        legs=(
            stock_leg("long_stock", LegDirection.BUY),
            option_leg("long_put", OptionType.PUT, LegDirection.BUY, group="hedge"),
        ),
        risk=directional_bounded,
    )
    add(
        name="collar",
        canonical_identifier="directional.collar",
        family=StrategyFamily.DIRECTIONAL,
        legs=(
            stock_leg("long_stock", LegDirection.BUY),
            option_leg("long_put", OptionType.PUT, LegDirection.BUY, group="hedge"),
            option_leg("short_call", OptionType.CALL, LegDirection.SELL, group="income"),
        ),
        risk=directional_bounded,
    )
    add(
        name="synthetic_long_stock",
        canonical_identifier="directional.synthetic_long_stock",
        family=StrategyFamily.DIRECTIONAL,
        legs=(
            option_leg("long_call", OptionType.CALL, LegDirection.BUY, group="synthetic"),
            option_leg("short_put", OptionType.PUT, LegDirection.SELL, group="synthetic"),
        ),
        risk=unbounded_risk,
    )
    add(
        name="synthetic_short_stock",
        canonical_identifier="directional.synthetic_short_stock",
        family=StrategyFamily.DIRECTIONAL,
        legs=(
            option_leg("short_call", OptionType.CALL, LegDirection.SELL, group="synthetic"),
            option_leg("long_put", OptionType.PUT, LegDirection.BUY, group="synthetic"),
        ),
        risk=unbounded_risk,
    )
    add(
        name="risk_reversal",
        canonical_identifier="directional.risk_reversal",
        family=StrategyFamily.DIRECTIONAL,
        legs=(
            option_leg("short_put", OptionType.PUT, LegDirection.SELL, group="put_side"),
            option_leg("long_call", OptionType.CALL, LegDirection.BUY, group="call_side"),
        ),
        risk=unbounded_risk,
    )
    add(
        name="conversion",
        canonical_identifier="directional.conversion",
        family=StrategyFamily.DIRECTIONAL,
        legs=(
            stock_leg("long_stock", LegDirection.BUY),
            option_leg("long_put", OptionType.PUT, LegDirection.BUY, group="synthetic"),
            option_leg("short_call", OptionType.CALL, LegDirection.SELL, group="synthetic"),
        ),
        limitations=("not_risk_free", "interest_dividend_borrow_sensitive"),
        risk=directional_bounded,
    )
    add(
        name="reversal",
        canonical_identifier="directional.reversal",
        family=StrategyFamily.DIRECTIONAL,
        legs=(
            stock_leg("short_stock", LegDirection.SELL),
            option_leg("long_call", OptionType.CALL, LegDirection.BUY, group="synthetic"),
            option_leg("short_put", OptionType.PUT, LegDirection.SELL, group="synthetic"),
        ),
        limitations=("not_risk_free", "interest_dividend_borrow_sensitive"),
        risk=unbounded_risk,
    )

    # Verticals
    add(
        name="bull_call_spread",
        canonical_identifier="vertical.bull_call_spread",
        family=StrategyFamily.VERTICAL,
        legs=(
            option_leg(
                "long_call",
                OptionType.CALL,
                LegDirection.BUY,
                group="vertical",
                strike_hint="lower",
            ),
            option_leg(
                "short_call",
                OptionType.CALL,
                LegDirection.SELL,
                group="vertical",
                strike_hint="higher",
            ),
        ),
    )
    add(
        name="bear_call_spread",
        canonical_identifier="vertical.bear_call_spread",
        family=StrategyFamily.VERTICAL,
        legs=(
            option_leg(
                "short_call",
                OptionType.CALL,
                LegDirection.SELL,
                group="vertical",
                strike_hint="lower",
            ),
            option_leg(
                "long_call",
                OptionType.CALL,
                LegDirection.BUY,
                group="vertical",
                strike_hint="higher",
            ),
        ),
    )
    add(
        name="bull_put_spread",
        canonical_identifier="vertical.bull_put_spread",
        family=StrategyFamily.VERTICAL,
        legs=(
            option_leg(
                "short_put",
                OptionType.PUT,
                LegDirection.SELL,
                group="vertical",
                strike_hint="higher",
            ),
            option_leg(
                "long_put", OptionType.PUT, LegDirection.BUY, group="vertical", strike_hint="lower"
            ),
        ),
    )
    add(
        name="bear_put_spread",
        canonical_identifier="vertical.bear_put_spread",
        family=StrategyFamily.VERTICAL,
        legs=(
            option_leg(
                "long_put", OptionType.PUT, LegDirection.BUY, group="vertical", strike_hint="higher"
            ),
            option_leg(
                "short_put",
                OptionType.PUT,
                LegDirection.SELL,
                group="vertical",
                strike_hint="lower",
            ),
        ),
    )
    add(
        name="call_debit_spread",
        canonical_identifier="vertical.call_debit_spread",
        family=StrategyFamily.VERTICAL,
        legs=(
            option_leg("long_call", OptionType.CALL, LegDirection.BUY, group="vertical"),
            option_leg("short_call", OptionType.CALL, LegDirection.SELL, group="vertical"),
        ),
    )
    add(
        name="call_credit_spread",
        canonical_identifier="vertical.call_credit_spread",
        family=StrategyFamily.VERTICAL,
        legs=(
            option_leg("short_call", OptionType.CALL, LegDirection.SELL, group="vertical"),
            option_leg("long_call", OptionType.CALL, LegDirection.BUY, group="vertical"),
        ),
    )
    add(
        name="put_debit_spread",
        canonical_identifier="vertical.put_debit_spread",
        family=StrategyFamily.VERTICAL,
        legs=(
            option_leg("long_put", OptionType.PUT, LegDirection.BUY, group="vertical"),
            option_leg("short_put", OptionType.PUT, LegDirection.SELL, group="vertical"),
        ),
    )
    add(
        name="put_credit_spread",
        canonical_identifier="vertical.put_credit_spread",
        family=StrategyFamily.VERTICAL,
        legs=(
            option_leg("short_put", OptionType.PUT, LegDirection.SELL, group="vertical"),
            option_leg("long_put", OptionType.PUT, LegDirection.BUY, group="vertical"),
        ),
    )

    # Iron structures
    add(
        name="iron_condor",
        canonical_identifier="iron.iron_condor",
        family=StrategyFamily.IRON,
        legs=(
            option_leg(
                "long_put_wing",
                OptionType.PUT,
                LegDirection.BUY,
                group="put_side",
                strike_hint="lowest",
            ),
            option_leg(
                "short_put",
                OptionType.PUT,
                LegDirection.SELL,
                group="put_side",
                strike_hint="inner_low",
            ),
            option_leg(
                "short_call",
                OptionType.CALL,
                LegDirection.SELL,
                group="call_side",
                strike_hint="inner_high",
            ),
            option_leg(
                "long_call_wing",
                OptionType.CALL,
                LegDirection.BUY,
                group="call_side",
                strike_hint="highest",
            ),
        ),
    )
    add(
        name="iron_butterfly",
        canonical_identifier="iron.iron_butterfly",
        family=StrategyFamily.IRON,
        legs=(
            option_leg("long_put_wing", OptionType.PUT, LegDirection.BUY, group="put_side"),
            option_leg("short_put_body", OptionType.PUT, LegDirection.SELL, group="body"),
            option_leg("short_call_body", OptionType.CALL, LegDirection.SELL, group="body"),
            option_leg("long_call_wing", OptionType.CALL, LegDirection.BUY, group="call_side"),
        ),
    )
    add(
        name="reverse_iron_condor",
        canonical_identifier="iron.reverse_iron_condor",
        family=StrategyFamily.IRON,
        legs=(
            option_leg("short_put_wing", OptionType.PUT, LegDirection.SELL, group="put_side"),
            option_leg("long_put", OptionType.PUT, LegDirection.BUY, group="put_side"),
            option_leg("long_call", OptionType.CALL, LegDirection.BUY, group="call_side"),
            option_leg("short_call_wing", OptionType.CALL, LegDirection.SELL, group="call_side"),
        ),
        risk=unbounded_risk,
    )
    add(
        name="reverse_iron_butterfly",
        canonical_identifier="iron.reverse_iron_butterfly",
        family=StrategyFamily.IRON,
        legs=(
            option_leg("short_put_wing", OptionType.PUT, LegDirection.SELL, group="put_side"),
            option_leg("long_put_body", OptionType.PUT, LegDirection.BUY, group="body"),
            option_leg("long_call_body", OptionType.CALL, LegDirection.BUY, group="body"),
            option_leg("short_call_wing", OptionType.CALL, LegDirection.SELL, group="call_side"),
        ),
        risk=unbounded_risk,
    )
    add(
        name="unbalanced_iron_condor",
        canonical_identifier="iron.unbalanced_iron_condor",
        family=StrategyFamily.IRON,
        legs=(
            option_leg("long_put_wing", OptionType.PUT, LegDirection.BUY, group="put_side"),
            option_leg("short_put", OptionType.PUT, LegDirection.SELL, group="put_side"),
            option_leg("short_call", OptionType.CALL, LegDirection.SELL, group="call_side"),
            option_leg(
                "long_call_wing", OptionType.CALL, LegDirection.BUY, group="call_side", ratio=2
            ),
        ),
    )
    add(
        name="broken_wing_iron_butterfly",
        canonical_identifier="iron.broken_wing_iron_butterfly",
        family=StrategyFamily.IRON,
        legs=(
            option_leg("long_put_wing", OptionType.PUT, LegDirection.BUY, group="put_side"),
            option_leg("short_put_body", OptionType.PUT, LegDirection.SELL, group="body"),
            option_leg("short_call_body", OptionType.CALL, LegDirection.SELL, group="body"),
            option_leg("long_call_wing", OptionType.CALL, LegDirection.BUY, group="call_side"),
        ),
    )

    # Butterfly/condor
    add(
        name="long_call_butterfly",
        canonical_identifier="butterfly.long_call_butterfly",
        family=StrategyFamily.BUTTERFLY_CONDOR,
        legs=(
            option_leg("long_call_lower", OptionType.CALL, LegDirection.BUY, group="butterfly"),
            option_leg(
                "short_call_body", OptionType.CALL, LegDirection.SELL, group="butterfly", ratio=2
            ),
            option_leg("long_call_upper", OptionType.CALL, LegDirection.BUY, group="butterfly"),
        ),
    )
    add(
        name="long_put_butterfly",
        canonical_identifier="butterfly.long_put_butterfly",
        family=StrategyFamily.BUTTERFLY_CONDOR,
        legs=(
            option_leg("long_put_upper", OptionType.PUT, LegDirection.BUY, group="butterfly"),
            option_leg(
                "short_put_body", OptionType.PUT, LegDirection.SELL, group="butterfly", ratio=2
            ),
            option_leg("long_put_lower", OptionType.PUT, LegDirection.BUY, group="butterfly"),
        ),
    )
    add(
        name="short_call_butterfly",
        canonical_identifier="butterfly.short_call_butterfly",
        family=StrategyFamily.BUTTERFLY_CONDOR,
        legs=(
            option_leg("short_call_lower", OptionType.CALL, LegDirection.SELL, group="butterfly"),
            option_leg(
                "long_call_body", OptionType.CALL, LegDirection.BUY, group="butterfly", ratio=2
            ),
            option_leg("short_call_upper", OptionType.CALL, LegDirection.SELL, group="butterfly"),
        ),
        risk=unbounded_risk,
    )
    add(
        name="short_put_butterfly",
        canonical_identifier="butterfly.short_put_butterfly",
        family=StrategyFamily.BUTTERFLY_CONDOR,
        legs=(
            option_leg("short_put_upper", OptionType.PUT, LegDirection.SELL, group="butterfly"),
            option_leg(
                "long_put_body", OptionType.PUT, LegDirection.BUY, group="butterfly", ratio=2
            ),
            option_leg("short_put_lower", OptionType.PUT, LegDirection.SELL, group="butterfly"),
        ),
        risk=unbounded_risk,
    )
    add(
        name="broken_wing_butterfly",
        canonical_identifier="butterfly.broken_wing_butterfly",
        family=StrategyFamily.BUTTERFLY_CONDOR,
        legs=(
            option_leg("long_wing_low", OptionType.CALL, LegDirection.BUY, group="butterfly"),
            option_leg(
                "short_body", OptionType.CALL, LegDirection.SELL, group="butterfly", ratio=2
            ),
            option_leg("long_wing_high", OptionType.CALL, LegDirection.BUY, group="butterfly"),
        ),
    )
    add(
        name="call_condor",
        canonical_identifier="condor.call_condor",
        family=StrategyFamily.BUTTERFLY_CONDOR,
        legs=(
            option_leg("long_call_1", OptionType.CALL, LegDirection.BUY, group="condor"),
            option_leg("short_call_2", OptionType.CALL, LegDirection.SELL, group="condor"),
            option_leg("short_call_3", OptionType.CALL, LegDirection.SELL, group="condor"),
            option_leg("long_call_4", OptionType.CALL, LegDirection.BUY, group="condor"),
        ),
    )
    add(
        name="put_condor",
        canonical_identifier="condor.put_condor",
        family=StrategyFamily.BUTTERFLY_CONDOR,
        legs=(
            option_leg("long_put_1", OptionType.PUT, LegDirection.BUY, group="condor"),
            option_leg("short_put_2", OptionType.PUT, LegDirection.SELL, group="condor"),
            option_leg("short_put_3", OptionType.PUT, LegDirection.SELL, group="condor"),
            option_leg("long_put_4", OptionType.PUT, LegDirection.BUY, group="condor"),
        ),
    )
    add(
        name="short_condor",
        canonical_identifier="condor.short_condor",
        family=StrategyFamily.BUTTERFLY_CONDOR,
        legs=(
            option_leg("short_wing_1", OptionType.CALL, LegDirection.SELL, group="condor"),
            option_leg("long_inner_2", OptionType.CALL, LegDirection.BUY, group="condor"),
            option_leg("long_inner_3", OptionType.CALL, LegDirection.BUY, group="condor"),
            option_leg("short_wing_4", OptionType.CALL, LegDirection.SELL, group="condor"),
        ),
        risk=unbounded_risk,
    )

    # Volatility
    add(
        name="long_straddle",
        canonical_identifier="volatility.long_straddle",
        family=StrategyFamily.VOLATILITY,
        legs=(
            option_leg("long_call", OptionType.CALL, LegDirection.BUY, group="body"),
            option_leg("long_put", OptionType.PUT, LegDirection.BUY, group="body"),
        ),
        risk=directional_bounded,
    )
    add(
        name="short_straddle",
        canonical_identifier="volatility.short_straddle",
        family=StrategyFamily.VOLATILITY,
        legs=(
            option_leg("short_call", OptionType.CALL, LegDirection.SELL, group="body"),
            option_leg("short_put", OptionType.PUT, LegDirection.SELL, group="body"),
        ),
        risk=unbounded_risk,
        limitations=("unlimited_risk", "event_sensitive", "assignment_sensitive"),
    )
    add(
        name="long_strangle",
        canonical_identifier="volatility.long_strangle",
        family=StrategyFamily.VOLATILITY,
        legs=(
            option_leg("long_call", OptionType.CALL, LegDirection.BUY, group="body"),
            option_leg("long_put", OptionType.PUT, LegDirection.BUY, group="body"),
        ),
        risk=directional_bounded,
    )
    add(
        name="short_strangle",
        canonical_identifier="volatility.short_strangle",
        family=StrategyFamily.VOLATILITY,
        legs=(
            option_leg("short_call", OptionType.CALL, LegDirection.SELL, group="body"),
            option_leg("short_put", OptionType.PUT, LegDirection.SELL, group="body"),
        ),
        risk=unbounded_risk,
        limitations=("unlimited_risk",),
    )
    add(
        name="strip",
        canonical_identifier="volatility.strip",
        family=StrategyFamily.VOLATILITY,
        legs=(
            option_leg("long_call", OptionType.CALL, LegDirection.BUY, group="body"),
            option_leg("long_puts", OptionType.PUT, LegDirection.BUY, group="body", ratio=2),
        ),
        risk=directional_bounded,
    )
    add(
        name="strap",
        canonical_identifier="volatility.strap",
        family=StrategyFamily.VOLATILITY,
        legs=(
            option_leg("long_calls", OptionType.CALL, LegDirection.BUY, group="body", ratio=2),
            option_leg("long_put", OptionType.PUT, LegDirection.BUY, group="body"),
        ),
        risk=directional_bounded,
    )
    add(
        name="gut_straddle",
        canonical_identifier="volatility.gut_straddle",
        family=StrategyFamily.VOLATILITY,
        legs=(
            option_leg("long_itm_call", OptionType.CALL, LegDirection.BUY, group="body"),
            option_leg("long_itm_put", OptionType.PUT, LegDirection.BUY, group="body"),
        ),
        risk=directional_bounded,
    )
    add(
        name="gut_strangle",
        canonical_identifier="volatility.gut_strangle",
        family=StrategyFamily.VOLATILITY,
        legs=(
            option_leg("long_itm_call", OptionType.CALL, LegDirection.BUY, group="body"),
            option_leg("long_itm_put", OptionType.PUT, LegDirection.BUY, group="body"),
        ),
        risk=directional_bounded,
    )

    # Calendar/diagonal
    add(
        name="call_calendar",
        canonical_identifier="calendar.call_calendar",
        family=StrategyFamily.CALENDAR_DIAGONAL,
        legs=(
            option_leg(
                "short_front_call",
                OptionType.CALL,
                LegDirection.SELL,
                group="front",
                expiry_hint="front",
            ),
            option_leg(
                "long_back_call",
                OptionType.CALL,
                LegDirection.BUY,
                group="back",
                expiry_hint="back",
            ),
        ),
        risk=calendar_risk,
    )
    add(
        name="put_calendar",
        canonical_identifier="calendar.put_calendar",
        family=StrategyFamily.CALENDAR_DIAGONAL,
        legs=(
            option_leg(
                "short_front_put",
                OptionType.PUT,
                LegDirection.SELL,
                group="front",
                expiry_hint="front",
            ),
            option_leg(
                "long_back_put", OptionType.PUT, LegDirection.BUY, group="back", expiry_hint="back"
            ),
        ),
        risk=calendar_risk,
    )
    add(
        name="atm_calendar",
        canonical_identifier="calendar.atm_calendar",
        family=StrategyFamily.CALENDAR_DIAGONAL,
        legs=(
            option_leg(
                "short_front_atm",
                OptionType.CALL,
                LegDirection.SELL,
                group="front",
                expiry_hint="front",
            ),
            option_leg(
                "long_back_atm", OptionType.CALL, LegDirection.BUY, group="back", expiry_hint="back"
            ),
        ),
        risk=calendar_risk,
    )
    add(
        name="otm_calendar",
        canonical_identifier="calendar.otm_calendar",
        family=StrategyFamily.CALENDAR_DIAGONAL,
        legs=(
            option_leg(
                "short_front_otm",
                OptionType.CALL,
                LegDirection.SELL,
                group="front",
                expiry_hint="front",
            ),
            option_leg(
                "long_back_otm", OptionType.CALL, LegDirection.BUY, group="back", expiry_hint="back"
            ),
        ),
        risk=calendar_risk,
    )
    add(
        name="double_calendar",
        canonical_identifier="calendar.double_calendar",
        family=StrategyFamily.CALENDAR_DIAGONAL,
        legs=(
            option_leg(
                "short_front_put",
                OptionType.PUT,
                LegDirection.SELL,
                group="front",
                expiry_hint="front",
            ),
            option_leg(
                "long_back_put", OptionType.PUT, LegDirection.BUY, group="back", expiry_hint="back"
            ),
            option_leg(
                "short_front_call",
                OptionType.CALL,
                LegDirection.SELL,
                group="front",
                expiry_hint="front",
            ),
            option_leg(
                "long_back_call",
                OptionType.CALL,
                LegDirection.BUY,
                group="back",
                expiry_hint="back",
            ),
        ),
        risk=calendar_risk,
    )
    add(
        name="ratio_calendar",
        canonical_identifier="calendar.ratio_calendar",
        family=StrategyFamily.CALENDAR_DIAGONAL,
        legs=(
            option_leg(
                "short_front",
                OptionType.CALL,
                LegDirection.SELL,
                group="front",
                ratio=2,
                expiry_hint="front",
            ),
            option_leg(
                "long_back",
                OptionType.CALL,
                LegDirection.BUY,
                group="back",
                ratio=1,
                expiry_hint="back",
            ),
        ),
        risk=calendar_risk,
    )
    add(
        name="horizontal_calendar",
        canonical_identifier="calendar.horizontal_calendar",
        family=StrategyFamily.CALENDAR_DIAGONAL,
        legs=(
            option_leg(
                "short_front",
                OptionType.CALL,
                LegDirection.SELL,
                group="front",
                expiry_hint="front",
            ),
            option_leg(
                "long_back", OptionType.CALL, LegDirection.BUY, group="back", expiry_hint="back"
            ),
        ),
        risk=calendar_risk,
    )
    add(
        name="call_diagonal",
        canonical_identifier="diagonal.call_diagonal",
        family=StrategyFamily.CALENDAR_DIAGONAL,
        legs=(
            option_leg(
                "short_front_otm",
                OptionType.CALL,
                LegDirection.SELL,
                group="front",
                expiry_hint="front",
            ),
            option_leg(
                "long_back_itm", OptionType.CALL, LegDirection.BUY, group="back", expiry_hint="back"
            ),
        ),
        risk=calendar_risk,
    )
    add(
        name="put_diagonal",
        canonical_identifier="diagonal.put_diagonal",
        family=StrategyFamily.CALENDAR_DIAGONAL,
        legs=(
            option_leg(
                "short_front_otm",
                OptionType.PUT,
                LegDirection.SELL,
                group="front",
                expiry_hint="front",
            ),
            option_leg(
                "long_back_itm", OptionType.PUT, LegDirection.BUY, group="back", expiry_hint="back"
            ),
        ),
        risk=calendar_risk,
    )
    add(
        name="double_diagonal",
        canonical_identifier="diagonal.double_diagonal",
        family=StrategyFamily.CALENDAR_DIAGONAL,
        legs=(
            option_leg(
                "short_front_put",
                OptionType.PUT,
                LegDirection.SELL,
                group="front",
                expiry_hint="front",
            ),
            option_leg(
                "long_back_put", OptionType.PUT, LegDirection.BUY, group="back", expiry_hint="back"
            ),
            option_leg(
                "short_front_call",
                OptionType.CALL,
                LegDirection.SELL,
                group="front",
                expiry_hint="front",
            ),
            option_leg(
                "long_back_call",
                OptionType.CALL,
                LegDirection.BUY,
                group="back",
                expiry_hint="back",
            ),
        ),
        risk=calendar_risk,
    )
    add(
        name="ratio_diagonal",
        canonical_identifier="diagonal.ratio_diagonal",
        family=StrategyFamily.CALENDAR_DIAGONAL,
        legs=(
            option_leg(
                "short_front",
                OptionType.CALL,
                LegDirection.SELL,
                group="front",
                ratio=2,
                expiry_hint="front",
            ),
            option_leg(
                "long_back",
                OptionType.CALL,
                LegDirection.BUY,
                group="back",
                ratio=1,
                expiry_hint="back",
            ),
        ),
        risk=calendar_risk,
    )
    add(
        name="earnings_calendar",
        canonical_identifier="calendar.earnings_calendar",
        family=StrategyFamily.CALENDAR_DIAGONAL,
        legs=(
            option_leg(
                "short_earnings_week",
                OptionType.CALL,
                LegDirection.SELL,
                group="front",
                expiry_hint="front",
            ),
            option_leg(
                "long_back_month",
                OptionType.CALL,
                LegDirection.BUY,
                group="back",
                expiry_hint="back",
            ),
        ),
        risk=calendar_risk,
    )
    add(
        name="pre_earnings_calendar",
        canonical_identifier="calendar.pre_earnings_calendar",
        family=StrategyFamily.CALENDAR_DIAGONAL,
        legs=(
            option_leg(
                "short_pre_earnings",
                OptionType.CALL,
                LegDirection.SELL,
                group="front",
                expiry_hint="front",
            ),
            option_leg(
                "long_back", OptionType.CALL, LegDirection.BUY, group="back", expiry_hint="back"
            ),
        ),
        risk=calendar_risk,
    )
    add(
        name="post_earnings_calendar",
        canonical_identifier="calendar.post_earnings_calendar",
        family=StrategyFamily.CALENDAR_DIAGONAL,
        legs=(
            option_leg(
                "short_post_earnings",
                OptionType.CALL,
                LegDirection.SELL,
                group="front",
                expiry_hint="front",
            ),
            option_leg(
                "long_back", OptionType.CALL, LegDirection.BUY, group="back", expiry_hint="back"
            ),
        ),
        risk=calendar_risk,
    )

    # Covered and replacement
    add(
        name="traditional_covered_call",
        canonical_identifier="covered.traditional_covered_call",
        family=StrategyFamily.COVERED_REPLACEMENT,
        legs=(
            stock_leg("long_stock", LegDirection.BUY),
            option_leg("short_call", OptionType.CALL, LegDirection.SELL, group="income"),
        ),
        risk=covered_risk,
    )
    add(
        name="pmcc",
        canonical_identifier="covered.pmcc",
        family=StrategyFamily.COVERED_REPLACEMENT,
        legs=(
            option_leg(
                "long_leaps_call",
                OptionType.CALL,
                LegDirection.BUY,
                group="replacement",
                expiry_hint="back",
            ),
            option_leg(
                "short_call",
                OptionType.CALL,
                LegDirection.SELL,
                group="income",
                expiry_hint="front",
            ),
        ),
        risk=calendar_risk,
    )
    add(
        name="synthetic_covered_call",
        canonical_identifier="covered.synthetic_covered_call",
        family=StrategyFamily.COVERED_REPLACEMENT,
        legs=(
            option_leg(
                "long_deep_itm_call", OptionType.CALL, LegDirection.BUY, group="replacement"
            ),
            option_leg("short_call", OptionType.CALL, LegDirection.SELL, group="income"),
        ),
        risk=covered_risk,
    )
    add(
        name="stock_replacement_long_call",
        canonical_identifier="covered.stock_replacement_long_call",
        family=StrategyFamily.COVERED_REPLACEMENT,
        legs=(
            option_leg(
                "long_replacement_call", OptionType.CALL, LegDirection.BUY, group="replacement"
            ),
        ),
        risk=directional_bounded,
    )
    add(
        name="leaps_diagonal",
        canonical_identifier="covered.leaps_diagonal",
        family=StrategyFamily.COVERED_REPLACEMENT,
        legs=(
            option_leg(
                "long_leaps_call",
                OptionType.CALL,
                LegDirection.BUY,
                group="replacement",
                expiry_hint="back",
            ),
            option_leg(
                "short_monthly_call",
                OptionType.CALL,
                LegDirection.SELL,
                group="income",
                expiry_hint="front",
            ),
        ),
        risk=calendar_risk,
    )
    add(
        name="covered_strangle",
        canonical_identifier="covered.covered_strangle",
        family=StrategyFamily.COVERED_REPLACEMENT,
        legs=(
            stock_leg("long_stock", LegDirection.BUY),
            option_leg("short_call", OptionType.CALL, LegDirection.SELL, group="income"),
            option_leg("short_put", OptionType.PUT, LegDirection.SELL, group="income"),
        ),
        risk=unbounded_risk,
    )
    add(
        name="wheel_strategy_state_template",
        canonical_identifier="covered.wheel_strategy_state_template",
        family=StrategyFamily.COVERED_REPLACEMENT,
        legs=(
            cash_leg("cash_phase"),
            option_leg("short_put_phase", OptionType.PUT, LegDirection.SELL, group="wheel"),
            stock_leg("assigned_stock_phase", LegDirection.BUY),
            option_leg("covered_call_phase", OptionType.CALL, LegDirection.SELL, group="wheel"),
        ),
        risk=covered_risk,
    )

    # Ratio and backspreads
    add(
        name="call_ratio_spread",
        canonical_identifier="ratio.call_ratio_spread",
        family=StrategyFamily.RATIO_BACKSPREAD,
        legs=(
            option_leg("long_call", OptionType.CALL, LegDirection.BUY, group="ratio"),
            option_leg("short_calls", OptionType.CALL, LegDirection.SELL, group="ratio", ratio=2),
        ),
        risk=unbounded_risk,
    )
    add(
        name="put_ratio_spread",
        canonical_identifier="ratio.put_ratio_spread",
        family=StrategyFamily.RATIO_BACKSPREAD,
        legs=(
            option_leg("long_put", OptionType.PUT, LegDirection.BUY, group="ratio"),
            option_leg("short_puts", OptionType.PUT, LegDirection.SELL, group="ratio", ratio=2),
        ),
        risk=unbounded_risk,
    )
    add(
        name="call_backspread",
        canonical_identifier="ratio.call_backspread",
        family=StrategyFamily.RATIO_BACKSPREAD,
        legs=(
            option_leg("short_call", OptionType.CALL, LegDirection.SELL, group="ratio"),
            option_leg("long_calls", OptionType.CALL, LegDirection.BUY, group="ratio", ratio=2),
        ),
        risk=unbounded_risk,
    )
    add(
        name="put_backspread",
        canonical_identifier="ratio.put_backspread",
        family=StrategyFamily.RATIO_BACKSPREAD,
        legs=(
            option_leg("short_put", OptionType.PUT, LegDirection.SELL, group="ratio"),
            option_leg("long_puts", OptionType.PUT, LegDirection.BUY, group="ratio", ratio=2),
        ),
        risk=unbounded_risk,
    )
    add(
        name="front_spread",
        canonical_identifier="ratio.front_spread",
        family=StrategyFamily.RATIO_BACKSPREAD,
        legs=(
            option_leg(
                "long_front",
                OptionType.CALL,
                LegDirection.BUY,
                group="ratio",
                expiry_hint="front",
                ratio=2,
            ),
            option_leg(
                "short_back", OptionType.CALL, LegDirection.SELL, group="ratio", expiry_hint="back"
            ),
        ),
        risk=unbounded_risk,
    )
    add(
        name="backspread",
        canonical_identifier="ratio.backspread",
        family=StrategyFamily.RATIO_BACKSPREAD,
        legs=(
            option_leg("short_body", OptionType.CALL, LegDirection.SELL, group="ratio"),
            option_leg("long_wings", OptionType.CALL, LegDirection.BUY, group="ratio", ratio=2),
        ),
        risk=unbounded_risk,
    )

    # Jade lizard and related
    add(
        name="jade_lizard",
        canonical_identifier="lizard.jade_lizard",
        family=StrategyFamily.LIZARD_VARIANTS,
        legs=(
            option_leg("short_put", OptionType.PUT, LegDirection.SELL, group="put_side"),
            option_leg("short_call", OptionType.CALL, LegDirection.SELL, group="call_spread"),
            option_leg("long_call_wing", OptionType.CALL, LegDirection.BUY, group="call_spread"),
        ),
        risk=unbounded_risk,
    )
    add(
        name="reverse_jade_lizard",
        canonical_identifier="lizard.reverse_jade_lizard",
        family=StrategyFamily.LIZARD_VARIANTS,
        legs=(
            option_leg("long_put", OptionType.PUT, LegDirection.BUY, group="put_side"),
            option_leg("long_call", OptionType.CALL, LegDirection.BUY, group="call_spread"),
            option_leg("short_call_wing", OptionType.CALL, LegDirection.SELL, group="call_spread"),
        ),
        risk=unbounded_risk,
    )
    add(
        name="big_lizard",
        canonical_identifier="lizard.big_lizard",
        family=StrategyFamily.LIZARD_VARIANTS,
        legs=(
            option_leg("short_put", OptionType.PUT, LegDirection.SELL, group="put_side"),
            option_leg("short_call", OptionType.CALL, LegDirection.SELL, group="call_spread"),
            option_leg(
                "long_call_wing", OptionType.CALL, LegDirection.BUY, group="call_spread", ratio=2
            ),
        ),
        risk=unbounded_risk,
    )
    add(
        name="twisted_sister",
        canonical_identifier="lizard.twisted_sister",
        family=StrategyFamily.LIZARD_VARIANTS,
        legs=(
            option_leg("short_put", OptionType.PUT, LegDirection.SELL, group="put_side"),
            option_leg("short_call", OptionType.CALL, LegDirection.SELL, group="call_side"),
            option_leg("long_put_wing", OptionType.PUT, LegDirection.BUY, group="put_side"),
            option_leg("long_call_wing", OptionType.CALL, LegDirection.BUY, group="call_side"),
        ),
        risk=directional_bounded,
    )
    add(
        name="seagull",
        canonical_identifier="lizard.seagull",
        family=StrategyFamily.LIZARD_VARIANTS,
        legs=(
            option_leg("long_call", OptionType.CALL, LegDirection.BUY, group="body"),
            option_leg("short_call", OptionType.CALL, LegDirection.SELL, group="wing"),
            option_leg("short_put", OptionType.PUT, LegDirection.SELL, group="wing"),
        ),
        risk=unbounded_risk,
    )
    add(
        name="fence",
        canonical_identifier="lizard.fence",
        family=StrategyFamily.LIZARD_VARIANTS,
        legs=(
            stock_leg("long_stock", LegDirection.BUY),
            option_leg("long_put", OptionType.PUT, LegDirection.BUY, group="hedge"),
            option_leg("short_call", OptionType.CALL, LegDirection.SELL, group="income"),
        ),
        risk=covered_risk,
    )

    # Box and arbitrage-style (research-only)
    add(
        name="long_box",
        canonical_identifier="arbitrage.long_box",
        family=StrategyFamily.BOX_ARBITRAGE,
        legs=(
            option_leg("long_call_low", OptionType.CALL, LegDirection.BUY, group="call_spread"),
            option_leg("short_call_high", OptionType.CALL, LegDirection.SELL, group="call_spread"),
            option_leg("long_put_high", OptionType.PUT, LegDirection.BUY, group="put_spread"),
            option_leg("short_put_low", OptionType.PUT, LegDirection.SELL, group="put_spread"),
        ),
        limitations=(
            "not_risk_free",
            "early_exercise_dividend_borrow_interest_sensitive",
            "transaction_cost_sensitive",
        ),
    )
    add(
        name="short_box",
        canonical_identifier="arbitrage.short_box",
        family=StrategyFamily.BOX_ARBITRAGE,
        legs=(
            option_leg("short_call_low", OptionType.CALL, LegDirection.SELL, group="call_spread"),
            option_leg("long_call_high", OptionType.CALL, LegDirection.BUY, group="call_spread"),
            option_leg("short_put_high", OptionType.PUT, LegDirection.SELL, group="put_spread"),
            option_leg("long_put_low", OptionType.PUT, LegDirection.BUY, group="put_spread"),
        ),
        limitations=("not_risk_free", "assignment_uncertainty"),
        risk=unbounded_risk,
    )
    add(
        name="jelly_roll",
        canonical_identifier="arbitrage.jelly_roll",
        family=StrategyFamily.BOX_ARBITRAGE,
        legs=(
            option_leg(
                "short_front_call",
                OptionType.CALL,
                LegDirection.SELL,
                group="front",
                expiry_hint="front",
            ),
            option_leg(
                "long_back_call",
                OptionType.CALL,
                LegDirection.BUY,
                group="back",
                expiry_hint="back",
            ),
            option_leg(
                "long_front_put",
                OptionType.PUT,
                LegDirection.BUY,
                group="front",
                expiry_hint="front",
            ),
            option_leg(
                "short_back_put",
                OptionType.PUT,
                LegDirection.SELL,
                group="back",
                expiry_hint="back",
            ),
        ),
        limitations=("not_risk_free",),
    )
    add(
        name="dividend_arbitrage_placeholder",
        canonical_identifier="arbitrage.dividend_arbitrage_placeholder",
        family=StrategyFamily.BOX_ARBITRAGE,
        legs=(
            stock_leg("long_stock", LegDirection.BUY),
            option_leg("short_call", OptionType.CALL, LegDirection.SELL, group="hedge"),
            option_leg("long_put", OptionType.PUT, LegDirection.BUY, group="hedge"),
        ),
        limitations=(
            "research_placeholder_only",
            "not_risk_free",
            "dividend_assignment_uncertainty",
        ),
        risk=covered_risk,
    )

    # Custom multi-leg shell
    add(
        name="custom_multi_leg",
        canonical_identifier="custom.custom_multi_leg",
        family=StrategyFamily.CUSTOM,
        legs=(option_leg("custom_leg_1", OptionType.CALL, LegDirection.BUY, group="custom"),),
        aliases=("custom",),
        limitations=("requires_user_supplied_leg_schema",),
    )

    return tuple(templates)


def _has_strike_ordering_issue(
    *,
    template: StrategyTemplate,
    selected_legs: tuple[StrategySelectedLeg, ...],
) -> bool:
    hints = [
        (leg.label, leg.strike_order_hint)
        for leg in template.legs
        if leg.strike_order_hint is not None
    ]
    if not hints:
        return False

    ranks = {
        "lowest": 0,
        "inner_low": 1,
        "body": 2,
        "inner_high": 3,
        "highest": 4,
        "lower": 0,
        "higher": 1,
    }
    mapped: list[tuple[int, float]] = []
    selected_by_label = {leg.label: leg for leg in selected_legs}
    for label, hint in hints:
        row = selected_by_label.get(label)
        if row is None or row.strike is None:
            continue
        rank = ranks.get(hint)
        if rank is None:
            continue
        mapped.append((rank, row.strike))
    if len(mapped) <= 1:
        return False

    ordered = sorted(mapped, key=lambda item: item[0])
    strikes = [item[1] for item in ordered]
    return any(right < left for left, right in zip(strikes, strikes[1:]))


def _has_expiration_ordering_issue(
    *,
    template: StrategyTemplate,
    selected_legs: tuple[StrategySelectedLeg, ...],
) -> bool:
    hinted = [leg for leg in template.legs if leg.expiration_order_hint in {"front", "back"}]
    if not hinted:
        return False

    selected_by_label = {leg.label: leg for leg in selected_legs}
    front_dates: list[date] = []
    back_dates: list[date] = []
    for leg in hinted:
        selected = selected_by_label.get(leg.label)
        if selected is None or selected.expiration is None:
            continue
        if leg.expiration_order_hint == "front":
            front_dates.append(selected.expiration)
        elif leg.expiration_order_hint == "back":
            back_dates.append(selected.expiration)
    if not front_dates or not back_dates:
        return False
    return max(front_dates) >= min(back_dates)


def _payoff_at_price(selected_legs: tuple[StrategySelectedLeg, ...], price: float) -> float:
    total = 0.0
    for leg in selected_legs:
        sign = 1.0 if leg.direction is LegDirection.BUY else -1.0
        qty = float(leg.quantity)
        mult = float(max(1, leg.multiplier))
        premium = float(leg.premium or 0.0)

        if leg.leg_kind is LegKind.CALL:
            strike = float(leg.strike or 0.0)
            intrinsic = max(0.0, price - strike)
            total += sign * qty * mult * (intrinsic - premium)
        elif leg.leg_kind is LegKind.PUT:
            strike = float(leg.strike or 0.0)
            intrinsic = max(0.0, strike - price)
            total += sign * qty * mult * (intrinsic - premium)
        elif leg.leg_kind is LegKind.STOCK:
            entry = float(leg.premium or 0.0)
            total += sign * qty * (price - entry)
        else:
            total += sign * qty * premium
    return total


def _breakeven_points(points: list[PayoffPoint]) -> tuple[float, ...]:
    out: list[float] = []
    for left, right in zip(points, points[1:]):
        if left.payoff == 0:
            out.append(left.underlying_price)
            continue
        if (left.payoff < 0 < right.payoff) or (left.payoff > 0 > right.payoff):
            span = right.underlying_price - left.underlying_price
            if span == 0:
                continue
            ratio = abs(left.payoff) / (abs(left.payoff) + abs(right.payoff))
            out.append(round(left.underlying_price + span * ratio, 8))
    return tuple(sorted(set(out)))


def _credit_or_debit(selected_legs: tuple[StrategySelectedLeg, ...]) -> PayoffTag:
    net = 0.0
    for leg in selected_legs:
        premium = float(leg.premium or 0.0)
        qty = float(leg.quantity) * float(max(1, leg.multiplier))
        if leg.direction is LegDirection.BUY:
            net -= premium * qty
        else:
            net += premium * qty
    if abs(net) < 1e-9:
        return PayoffTag.EVEN
    return PayoffTag.CREDIT if net > 0 else PayoffTag.DEBIT


def _intrinsic_total(selected_legs: tuple[StrategySelectedLeg, ...]) -> float | None:
    values = []
    for leg in selected_legs:
        if leg.leg_kind not in {LegKind.CALL, LegKind.PUT}:
            continue
        if leg.strike is None:
            return None
        spot = leg.strike
        if leg.leg_kind is LegKind.CALL:
            intrinsic = max(0.0, spot - leg.strike)
        else:
            intrinsic = max(0.0, leg.strike - spot)
        sign = 1.0 if leg.direction is LegDirection.BUY else -1.0
        values.append(sign * intrinsic * leg.quantity * max(1, leg.multiplier))
    if not values:
        return 0.0
    return round(sum(values), 8)


def _extrinsic_total(selected_legs: tuple[StrategySelectedLeg, ...]) -> float | None:
    values = []
    for leg in selected_legs:
        if leg.leg_kind not in {LegKind.CALL, LegKind.PUT}:
            continue
        if leg.premium is None:
            return None
        sign = 1.0 if leg.direction is LegDirection.BUY else -1.0
        values.append(sign * leg.premium * leg.quantity * max(1, leg.multiplier))
    if not values:
        return 0.0
    return round(sum(values), 8)


def _slope_regions(points: list[PayoffPoint]) -> tuple[str, ...]:
    if len(points) < 2:
        return ()
    labels: list[str] = []
    for left, right in zip(points, points[1:]):
        slope = right.payoff - left.payoff
        if slope > 0:
            labels.append("increasing")
        elif slope < 0:
            labels.append("decreasing")
        else:
            labels.append("flat")
    compressed: list[str] = []
    for label in labels:
        if not compressed or compressed[-1] != label:
            compressed.append(label)
    return tuple(compressed)
