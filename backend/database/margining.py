"""Persistence and query services for backtest margin, cash, borrow, and liquidation state."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict
from datetime import datetime
from hashlib import sha256

from backend.database.backtesting import BacktestMutationError
from backend.database.dtos import (
    BacktestAccountConfigurationDTO,
    BacktestBorrowAccrualDTO,
    BacktestBorrowRecordDTO,
    BacktestBrokerPolicyComparisonDTO,
    BacktestBuyingPowerSnapshotDTO,
    BacktestCashBalanceDTO,
    BacktestCashSettlementFlowDTO,
    BacktestCollateralRecordDTO,
    BacktestInterestAccrualDTO,
    BacktestLiquidationOutcomeDTO,
    BacktestLiquidationPlanDTO,
    BacktestLiquidationStepDTO,
    BacktestMarginCalculationDTO,
    BacktestMarginCallEventDTO,
    BacktestMarginPolicyDTO,
    BacktestMarginReconciliationDTO,
    BacktestMarginReproducibilityChecksumDTO,
)
from backend.database.models import (
    BacktestBuyingPowerSnapshotRecord,
    BacktestCashBalanceRecord,
    BacktestMarginCalculationRecord,
    BacktestMarginCallEventRecord,
)
from backend.database.repositories.backtesting import BacktestRunRepository
from backend.database.repositories.margining import (
    BacktestAccountConfigurationRepository,
    BacktestBorrowAccrualRepository,
    BacktestBorrowRecordRepository,
    BacktestBrokerPolicyComparisonRepository,
    BacktestBuyingPowerSnapshotRepository,
    BacktestCashBalanceRepository,
    BacktestCashSettlementFlowRepository,
    BacktestCollateralRecordRepository,
    BacktestInterestAccrualRepository,
    BacktestLiquidationOutcomeRepository,
    BacktestLiquidationPlanRepository,
    BacktestLiquidationStepRepository,
    BacktestMarginCalculationRepository,
    BacktestMarginCallEventRepository,
    BacktestMarginPolicyRepository,
    BacktestMarginReconciliationRepository,
    BacktestMarginReproducibilityChecksumRepository,
)
from backend.database.session import DatabaseSessionManager


class BacktestMarginPersistenceService:
    def __init__(self, session_manager: DatabaseSessionManager) -> None:
        self.session_manager = session_manager

    def store_run_state(
        self,
        *,
        run_id: str,
        account_configurations: list[BacktestAccountConfigurationDTO],
        margin_policies: list[BacktestMarginPolicyDTO],
        margin_calculations: list[BacktestMarginCalculationDTO],
        buying_power_snapshots: list[BacktestBuyingPowerSnapshotDTO],
        collateral_records: list[BacktestCollateralRecordDTO],
        cash_balances: list[BacktestCashBalanceDTO],
        cash_settlement_flows: list[BacktestCashSettlementFlowDTO],
        interest_accruals: list[BacktestInterestAccrualDTO],
        borrow_records: list[BacktestBorrowRecordDTO],
        borrow_accruals: list[BacktestBorrowAccrualDTO],
        margin_call_events: list[BacktestMarginCallEventDTO],
        liquidation_plans: list[BacktestLiquidationPlanDTO],
        liquidation_steps: list[BacktestLiquidationStepDTO],
        liquidation_outcomes: list[BacktestLiquidationOutcomeDTO],
        broker_policy_comparisons: list[BacktestBrokerPolicyComparisonDTO],
        reconciliation_records: list[BacktestMarginReconciliationDTO],
        reproducibility_checksums: list[BacktestMarginReproducibilityChecksumDTO],
    ) -> int:
        with self.session_manager.session_scope() as session:
            run_row = BacktestRunRepository(session).get_run(run_id)
            if run_row is None:
                raise BacktestMutationError(f"backtest run not found for margin state: {run_id}")
            run_row_id = run_row.id
            BacktestAccountConfigurationRepository(session).upsert_rows(
                [
                    {
                        "run_row_id": run_row_id,
                        **{
                            key: value
                            for key, value in asdict(item).items()
                            if key != "metadata_json"
                        },
                        **{
                            "metadata": item.metadata_json,
                        },
                    }
                    for item in account_configurations
                ]
            )
            BacktestMarginPolicyRepository(session).upsert_rows(
                [
                    {
                        "run_row_id": run_row_id,
                        **{
                            key: value
                            for key, value in asdict(item).items()
                            if key != "metadata_json"
                        },
                        **{
                            "metadata": item.metadata_json,
                        },
                    }
                    for item in margin_policies
                ]
            )
            BacktestMarginCalculationRepository(session).upsert_rows(
                [
                    {
                        "run_row_id": run_row_id,
                        **asdict(item),
                    }
                    for item in margin_calculations
                ]
            )
            BacktestBuyingPowerSnapshotRepository(session).upsert_rows(
                [{"run_row_id": run_row_id, **asdict(item)} for item in buying_power_snapshots]
            )
            BacktestCollateralRecordRepository(session).upsert_rows(
                [
                    {
                        "run_row_id": run_row_id,
                        **{
                            key: value
                            for key, value in asdict(item).items()
                            if key != "metadata_json"
                        },
                        **{
                            "metadata": item.metadata_json,
                        },
                    }
                    for item in collateral_records
                ]
            )
            BacktestCashBalanceRepository(session).upsert_rows(
                [
                    {
                        "run_row_id": run_row_id,
                        **{
                            key: value
                            for key, value in asdict(item).items()
                            if key != "metadata_json"
                        },
                        **{
                            "metadata": item.metadata_json,
                        },
                    }
                    for item in cash_balances
                ]
            )
            BacktestCashSettlementFlowRepository(session).upsert_rows(
                [
                    {
                        "run_row_id": run_row_id,
                        **{
                            key: value
                            for key, value in asdict(item).items()
                            if key != "metadata_json"
                        },
                        **{
                            "metadata": item.metadata_json,
                        },
                    }
                    for item in cash_settlement_flows
                ]
            )
            BacktestInterestAccrualRepository(session).upsert_rows(
                [
                    {
                        "run_row_id": run_row_id,
                        **asdict(item),
                    }
                    for item in interest_accruals
                ]
            )
            BacktestBorrowRecordRepository(session).upsert_rows(
                [
                    {
                        "run_row_id": run_row_id,
                        **{
                            key: value
                            for key, value in asdict(item).items()
                            if key != "metadata_json"
                        },
                        **{
                            "metadata": item.metadata_json,
                        },
                    }
                    for item in borrow_records
                ]
            )
            BacktestBorrowAccrualRepository(session).upsert_rows(
                [
                    {
                        "run_row_id": run_row_id,
                        **{
                            key: value
                            for key, value in asdict(item).items()
                            if key != "metadata_json"
                        },
                        **{
                            "metadata": item.metadata_json,
                        },
                    }
                    for item in borrow_accruals
                ]
            )
            BacktestMarginCallEventRepository(session).upsert_rows(
                [
                    {
                        "run_row_id": run_row_id,
                        **asdict(item),
                    }
                    for item in margin_call_events
                ]
            )
            BacktestLiquidationPlanRepository(session).upsert_rows(
                [{"run_row_id": run_row_id, **asdict(item)} for item in liquidation_plans]
            )
            BacktestLiquidationStepRepository(session).upsert_rows(
                [
                    {
                        "run_row_id": run_row_id,
                        **{
                            key: value
                            for key, value in asdict(item).items()
                            if key != "metadata_json"
                        },
                        **{
                            "metadata": item.metadata_json,
                        },
                    }
                    for item in liquidation_steps
                ]
            )
            BacktestLiquidationOutcomeRepository(session).upsert_rows(
                [
                    {
                        "run_row_id": run_row_id,
                        **asdict(item),
                    }
                    for item in liquidation_outcomes
                ]
            )
            BacktestBrokerPolicyComparisonRepository(session).upsert_rows(
                [
                    {
                        "run_row_id": run_row_id,
                        **asdict(item),
                    }
                    for item in broker_policy_comparisons
                ]
            )
            BacktestMarginReconciliationRepository(session).upsert_rows(
                [
                    {
                        "run_row_id": run_row_id,
                        **asdict(item),
                    }
                    for item in reconciliation_records
                ]
            )
            BacktestMarginReproducibilityChecksumRepository(session).upsert_rows(
                [
                    {
                        "run_row_id": run_row_id,
                        **{
                            key: value
                            for key, value in asdict(item).items()
                            if key != "metadata_json"
                        },
                        **{
                            "metadata": item.metadata_json,
                        },
                    }
                    for item in reproducibility_checksums
                ]
            )
            return run_row_id


class BacktestMarginQueryService:
    def __init__(self, session_manager: DatabaseSessionManager) -> None:
        self.session_manager = session_manager

    def account_state_as_of(
        self,
        *,
        run_id: str,
        account_id: str,
        as_of: datetime,
    ) -> tuple[
        BacktestCashBalanceRecord | None,
        BacktestBuyingPowerSnapshotRecord | None,
    ]:
        with self.session_manager.session_scope() as session:
            run_row = BacktestRunRepository(session).get_run(run_id)
            if run_row is None:
                return None, None
            cash = BacktestCashBalanceRepository(session).as_of(
                run_row_id=run_row.id,
                account_id=account_id,
                as_of=as_of,
            )
            buying_power = BacktestBuyingPowerSnapshotRepository(session).as_of(
                run_row_id=run_row.id,
                account_id=account_id,
                as_of=as_of,
            )
            return cash, buying_power

    def margin_history(
        self,
        *,
        run_id: str,
        account_id: str,
    ) -> Sequence[BacktestMarginCalculationRecord]:
        with self.session_manager.session_scope() as session:
            run_row = BacktestRunRepository(session).get_run(run_id)
            if run_row is None:
                return []
            return BacktestMarginCalculationRepository(session).history(
                run_row_id=run_row.id,
                account_id=account_id,
            )

    def cash_history(
        self,
        *,
        run_id: str,
        account_id: str,
    ) -> Sequence[BacktestCashBalanceRecord]:
        with self.session_manager.session_scope() as session:
            run_row = BacktestRunRepository(session).get_run(run_id)
            if run_row is None:
                return []
            return BacktestCashBalanceRepository(session).history(
                run_row_id=run_row.id,
                account_id=account_id,
            )

    def margin_calls(
        self,
        *,
        run_id: str,
        account_id: str,
    ) -> Sequence[BacktestMarginCallEventRecord]:
        with self.session_manager.session_scope() as session:
            run_row = BacktestRunRepository(session).get_run(run_id)
            if run_row is None:
                return []
            return BacktestMarginCallEventRepository(session).history(
                run_row_id=run_row.id,
                account_id=account_id,
            )


def deterministic_backtest_margin_checksum(
    *,
    run_id: str,
    margin_calculations: list[BacktestMarginCalculationDTO],
) -> str:
    payload = {
        "run_id": run_id,
        "margin_calculations": [
            {
                "calculation_id": item.calculation_id,
                "account_id": item.account_id,
                "event_timestamp": item.event_timestamp.isoformat(),
                "initial_requirement": str(item.initial_requirement),
                "maintenance_requirement": str(item.maintenance_requirement),
                "post_trade_buying_power": str(item.post_trade_buying_power),
            }
            for item in sorted(
                margin_calculations,
                key=lambda row: (row.event_timestamp, row.calculation_id),
            )
        ],
    }
    return sha256(repr(payload).encode("utf-8")).hexdigest()
