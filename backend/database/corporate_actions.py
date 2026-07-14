"""Corporate-action processing services and adjustment policy execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, time
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import select

from backend.database.dtos import (
    NormalizedCorporateActionDTO,
    RawVendorRecordDTO,
    SymbolHistoryDTO,
)
from backend.database.models import OptionContract, UnderlyingPrice
from backend.database.repositories import CorporateActionNormalizationRepository
from backend.database.session import DatabaseSessionManager


class CorporateActionKnowledgePolicy(StrEnum):
    EFFECTIVE_DATE = "effective-date"
    ANNOUNCEMENT_AWARE = "announcement-aware"


@dataclass(slots=True, frozen=True)
class AdjustmentPolicy:
    split_adjust_underlyings: bool = True
    dividend_adjust_underlyings: bool = False
    total_return_view: bool = False
    adjust_option_strikes_and_multipliers: bool = True
    resolve_symbol_history: bool = True
    apply_deliverable_changes: bool = True
    knowledge_policy: CorporateActionKnowledgePolicy = CorporateActionKnowledgePolicy.EFFECTIVE_DATE


@dataclass(slots=True, frozen=True)
class AdjustmentWarning:
    code: str
    message: str
    source_action_id: int | None = None


@dataclass(slots=True)
class AdjustmentRunResult:
    raw_inserted: int = 0
    normalized_upserted: int = 0
    symbol_updates: int = 0
    adjusted_underlying_rows: int = 0
    adjusted_contract_rows: int = 0
    warnings: list[AdjustmentWarning] = field(default_factory=list)


class CorporateActionService:
    """Persist corporate actions and build adjusted research views with no-look-ahead safeguards."""

    def __init__(self, session_manager: DatabaseSessionManager) -> None:
        self.session_manager = session_manager

    def insert_raw_and_normalized(
        self,
        *,
        raw_records: list[RawVendorRecordDTO],
        normalized_actions: list[NormalizedCorporateActionDTO],
        symbol_history: list[SymbolHistoryDTO] | None = None,
    ) -> AdjustmentRunResult:
        result = AdjustmentRunResult()

        with self.session_manager.session_scope() as session:
            repo = CorporateActionNormalizationRepository(session)
            repo.insert_raw_records([asdict(item) for item in raw_records])
            repo.upsert_normalized_actions(
                [_normalized_to_mapping(item) for item in normalized_actions]
            )
            if symbol_history:
                repo.upsert_symbol_history([asdict(item) for item in symbol_history])

            result.raw_inserted = len(raw_records)
            result.normalized_upserted = len(normalized_actions)
            result.symbol_updates = len(symbol_history or [])

        return result

    def resolve_symbol_history(
        self,
        *,
        symbol: str,
        as_of_date: date,
    ) -> str:
        with self.session_manager.session_scope() as session:
            repo = CorporateActionNormalizationRepository(session)
            return repo.resolve_symbol(symbol, as_of_date)

    def build_adjusted_underlying_view(
        self,
        *,
        underlying_id: int,
        as_of: datetime,
        view_name: str,
        policy: AdjustmentPolicy,
    ) -> AdjustmentRunResult:
        result = AdjustmentRunResult()

        with self.session_manager.session_scope() as session:
            repo = CorporateActionNormalizationRepository(session)
            actions = repo.actions_for_underlying(underlying_id)

            prices = list(
                session.execute(
                    select(UnderlyingPrice).where(
                        UnderlyingPrice.underlying_id == underlying_id,
                        UnderlyingPrice.price_timestamp <= as_of,
                    )
                ).scalars()
            )

            rows: list[dict[str, object]] = []
            for price in prices:
                applicable = _applicable_actions(
                    actions,
                    as_of=price.price_timestamp,
                    policy=policy,
                )
                adjusted = Decimal(price.price)
                details: list[dict[str, str]] = []

                for action in applicable:
                    action_type = action.action_type
                    if action_type in {"stock_split", "reverse_stock_split"}:
                        if not policy.split_adjust_underlyings:
                            continue
                        if action.ratio is None or action.ratio == 0:
                            result.warnings.append(
                                AdjustmentWarning(
                                    code="incomplete_split_information",
                                    message="Split action missing ratio; adjustment skipped",
                                    source_action_id=int(action.id),
                                )
                            )
                            continue
                        adjusted = adjusted / Decimal(action.ratio)
                        details.append({"action": action_type, "ratio": str(action.ratio)})
                    elif action_type in {"ordinary_dividend", "special_dividend"}:
                        if not policy.dividend_adjust_underlyings and not policy.total_return_view:
                            continue
                        if action.cash_amount is None:
                            result.warnings.append(
                                AdjustmentWarning(
                                    code="incomplete_dividend_information",
                                    message=(
                                        "Dividend action missing cash amount; adjustment skipped"
                                    ),
                                    source_action_id=int(action.id),
                                )
                            )
                            continue
                        adjusted = adjusted - Decimal(action.cash_amount)
                        details.append({"action": action_type, "cash": str(action.cash_amount)})

                row: dict[str, object] = {
                    "underlying_id": underlying_id,
                    "source_price_id": price.id,
                    "source_action_id": int(applicable[-1].id) if applicable else None,
                    "view_name": view_name,
                    "policy_name": policy.knowledge_policy.value,
                    "price_timestamp": price.price_timestamp,
                    "base_price": Decimal(price.price),
                    "adjusted_price": adjusted,
                    "adjustment_details": {"applied_actions": details},
                }
                rows.append(row)

            repo.upsert_adjusted_underlying_views(rows)
            result.adjusted_underlying_rows = len(rows)

        return result

    def build_adjusted_option_view(
        self,
        *,
        contract_id: int,
        as_of_date: date,
        view_name: str,
        policy: AdjustmentPolicy,
    ) -> AdjustmentRunResult:
        result = AdjustmentRunResult()

        with self.session_manager.session_scope() as session:
            repo = CorporateActionNormalizationRepository(session)
            contract = session.get(OptionContract, contract_id)
            if contract is None:
                result.warnings.append(
                    AdjustmentWarning(
                        code="missing_contract",
                        message="Option contract not found; no adjusted row created",
                    )
                )
                return result

            actions = repo.actions_for_underlying(contract.underlying_id)
            as_of_dt = datetime.combine(as_of_date, time(23, 59, 59), tzinfo=UTC)
            applicable = _applicable_actions(actions, as_of=as_of_dt, policy=policy)

            strike = Decimal(contract.strike)
            multiplier = Decimal(contract.multiplier)
            deliverable = None
            details: list[dict[str, str]] = []

            for action in applicable:
                action_type = action.action_type
                if action_type in {"stock_split", "reverse_stock_split"}:
                    if not policy.adjust_option_strikes_and_multipliers:
                        continue
                    if action.ratio is None or action.ratio == 0:
                        result.warnings.append(
                            AdjustmentWarning(
                                code="incomplete_contract_adjustment",
                                message="Split ratio missing for contract adjustment",
                                source_action_id=int(action.id),
                            )
                        )
                        continue
                    strike = strike / Decimal(action.ratio)
                    multiplier = multiplier * Decimal(action.ratio)
                    details.append({"action": action_type, "ratio": str(action.ratio)})

                if action_type == "multiplier_change":
                    if action.multiplier_after is None:
                        result.warnings.append(
                            AdjustmentWarning(
                                code="incomplete_multiplier_change",
                                message="Multiplier change missing multiplier_after",
                                source_action_id=int(action.id),
                            )
                        )
                        continue
                    multiplier = Decimal(action.multiplier_after)
                    details.append({"action": action_type, "multiplier_after": str(multiplier)})

                if action_type == "deliverable_change" and policy.apply_deliverable_changes:
                    if not action.deliverable_after:
                        result.warnings.append(
                            AdjustmentWarning(
                                code="incomplete_deliverable_change",
                                message="Deliverable change missing deliverable_after",
                                source_action_id=int(action.id),
                            )
                        )
                        continue
                    deliverable = action.deliverable_after
                    details.append({"action": action_type, "deliverable_after": deliverable})

            repo.upsert_adjusted_option_views(
                [
                    {
                        "contract_id": contract_id,
                        "source_action_id": int(applicable[-1].id) if applicable else None,
                        "view_name": view_name,
                        "policy_name": policy.knowledge_policy.value,
                        "as_of_date": as_of_date,
                        "adjusted_strike": strike,
                        "adjusted_multiplier": multiplier,
                        "deliverable_after": deliverable,
                        "adjustment_details": {"applied_actions": details},
                    }
                ]
            )
            result.adjusted_contract_rows = 1

        return result


def _applicable_actions(
    actions: list[Any],
    *,
    as_of: datetime,
    policy: AdjustmentPolicy,
) -> list[Any]:
    return [
        action
        for action in actions
        if _is_action_knowable(
            effective_date=action.effective_date,
            announcement_timestamp=action.announcement_timestamp,
            as_of=as_of,
            policy=policy.knowledge_policy,
        )
    ]


def _is_action_knowable(
    *,
    effective_date: date,
    announcement_timestamp: datetime | None,
    as_of: datetime,
    policy: CorporateActionKnowledgePolicy,
) -> bool:
    as_of_utc = _ensure_timezone_aware(as_of)
    if policy == CorporateActionKnowledgePolicy.EFFECTIVE_DATE:
        return effective_date <= as_of_utc.date()
    if announcement_timestamp is None:
        return False
    return _ensure_timezone_aware(announcement_timestamp) <= as_of_utc


def _normalized_to_mapping(item: NormalizedCorporateActionDTO) -> dict[str, object]:
    payload = asdict(item)
    payload["action_type"] = item.action_type.value
    return payload


def _ensure_timezone_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
