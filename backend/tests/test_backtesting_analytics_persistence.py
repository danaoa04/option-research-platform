from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import create_engine, select

from backend.database import (
    BacktestArbitrationDecisionDTO,
    BacktestComparisonRunDTO,
    BacktestEventOverlayDTO,
    BacktestExportMetadataDTO,
    BacktestGreeksAttributionDTO,
    BacktestPersistenceService,
    BacktestPnLAttributionDTO,
    BacktestPortfolioAnalyticsDTO,
    BacktestReconstructedTradeDTO,
    BacktestReplaySnapshotDTO,
    BacktestRunDTO,
    BacktestStrategyAnalyticsDTO,
    BacktestStrategyCycleDTO,
)
from backend.database.models import (
    BacktestArbitrationDecisionRecord,
    BacktestComparisonRunRecord,
    BacktestEventOverlayRecord,
    BacktestExportMetadataRecord,
    BacktestGreeksAttributionRecord,
    BacktestPnLAttributionRecord,
    BacktestPortfolioAnalyticsRecord,
    BacktestReconstructedTradeRecord,
    BacktestReplaySnapshotRecord,
    BacktestStrategyAnalyticsRecord,
    BacktestStrategyCycleRecord,
    Base,
)
from backend.database.session import DatabaseSessionManager


def test_backtest_analytics_replay_persistence_round_trip() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    manager = DatabaseSessionManager(engine)
    service = BacktestPersistenceService(manager)
    timestamp = datetime(2026, 6, 4, 14, 30, tzinfo=UTC)

    run = BacktestRunDTO(
        run_id="bt-s6c-1",
        strategy_name="calendar_spread",
        started_at=timestamp,
        ended_at=timestamp,
        configuration_json={"symbols": ["SPY"]},
        status="completed",
        reproducibility_json={
            "event_ordering": "timestamp_priority_sequence",
            "information_set_policy": "no_look_ahead",
            "lookup_policies": {"quotes": "nearest_prior"},
            "dataset_manifests": ["m-1"],
            "fill_policies": {"mode": "midpoint"},
            "lifecycle_policies": {"profit_target": 0.5},
        },
        checksums={"state": "abc"},
        metadata_json={"sprint": "6C"},
        software_git_commit="deadbeef",
        schema_version="6.2",
        random_seed=19,
        created_at=timestamp,
    )

    service.store_run(
        run,
        events=[],
        order_intents=[],
        fills=[],
        positions=[],
        position_legs=[],
        valuations=[],
        cash_ledger=[],
        snapshots=[],
        lifecycle_triggers=[],
        run_comparisons=[],
        scenarios=[],
        reproducibility_checksums=[],
        strategy_analytics=[
            BacktestStrategyAnalyticsDTO(
                strategy_instance_id="si-1",
                snapshot_timestamp=timestamp,
                realized_pnl=Decimal("10"),
                unrealized_pnl=Decimal("2"),
                total_pnl=Decimal("12"),
                return_value=Decimal("0.012"),
                capital_usage=Decimal("500"),
                cash_usage=Decimal("250"),
                intrinsic_value=Decimal("1"),
                extrinsic_value=Decimal("3"),
                greeks={"delta": 0.2},
                implied_volatility=Decimal("0.2"),
                realized_volatility=Decimal("0.18"),
                iv_rank=Decimal("0.6"),
                iv_percentile=Decimal("0.7"),
                term_structure_json={"slope": 0.01},
                liquidity_json={"score": 0.9},
                lifecycle_state="open",
                warnings=[],
                failures=[],
            )
        ],
        portfolio_analytics=[
            BacktestPortfolioAnalyticsDTO(
                snapshot_timestamp=timestamp,
                equity=Decimal("10050"),
                cash=Decimal("9000"),
                reserved_capital=Decimal("500"),
                capital_utilization=Decimal("0.1"),
                realized_pnl=Decimal("10"),
                unrealized_pnl=Decimal("40"),
                greeks={"delta": 0.3},
                exposures_json={"symbol": {"SPY": 1.0}},
                risk_json={"es": 0.02},
            )
        ],
        pnl_attributions=[
            BacktestPnLAttributionDTO(
                strategy_instance_id="si-1",
                snapshot_timestamp=timestamp,
                factors_json={"theta": 1.2},
                approximation=True,
            )
        ],
        greeks_attributions=[
            BacktestGreeksAttributionDTO(
                strategy_instance_id="si-1",
                snapshot_timestamp=timestamp,
                greek_changes={"delta": 0.01},
                attributable_to={"underlying": 0.6},
            )
        ],
        reconstructed_trades=[
            BacktestReconstructedTradeDTO(
                trade_id="t-1",
                strategy_id="s-1",
                position_id="p-1",
                lifecycle_json={"entry": {}, "close": {}},
                cash_movements=Decimal("-200"),
                realized_pnl=Decimal("12"),
                fees=Decimal("1.5"),
                final_state="closed",
                source_event_ids=["e-1"],
                source_checksums=["c-1"],
            )
        ],
        strategy_cycles=[
            BacktestStrategyCycleDTO(
                cycle_id="cycle-1",
                strategy_id="s-1",
                initial_position="p-1",
                child_positions=["p-2"],
                roll_chain=["t-2"],
                cumulative_debit_credit=Decimal("-200"),
                cumulative_fees=Decimal("2"),
                cumulative_pnl=Decimal("12"),
                maximum_capital_usage=Decimal("500"),
                total_holding_duration_seconds=Decimal("3600"),
                final_result="closed",
                lifecycle_reasons=["profit_target"],
            )
        ],
        replay_snapshots=[
            BacktestReplaySnapshotDTO(
                snapshot_id="snap-1",
                cursor=7,
                snapshot_timestamp=timestamp,
                payload_json={"portfolio": {"cash": 9000}},
                source_checksums={"events": "abc"},
            )
        ],
        event_overlays=[
            BacktestEventOverlayDTO(
                event_sequence_number=7,
                event_type="earnings_announcement",
                priority=60,
                effective_timestamp=timestamp,
                overlay_json={"hours_to_earnings": 24},
            )
        ],
        arbitration_decisions=[
            BacktestArbitrationDecisionDTO(
                decision_id="arb-1",
                decision_timestamp=timestamp,
                policy="risk_first",
                accepted_actions=[{"action_id": "a-1"}],
                rejected_actions=[{"action_id": "a-2", "reason": "capital"}],
                diagnostics={"remaining_capital": 1000},
            )
        ],
        comparison_runs=[
            BacktestComparisonRunDTO(
                comparison_id="cmp-1",
                left_run_id="run-a",
                right_run_id="run-b",
                comparison_key="equity_curve",
                table_rows=[{"timestamp": "t", "delta": 1.0}],
                chart_payload={"series": []},
                created_at=timestamp,
            )
        ],
        export_metadata=[
            BacktestExportMetadataDTO(
                export_id="exp-1",
                export_kind="json",
                artifact_path="exports/run-1.json",
                artifact_checksum="sha256:abc",
                metadata_json={"api_version": "v1"},
                created_at=timestamp,
            )
        ],
    )

    with manager.session_scope() as session:
        assert session.execute(select(BacktestStrategyAnalyticsRecord)).scalars().all()
        assert session.execute(select(BacktestPortfolioAnalyticsRecord)).scalars().all()
        assert session.execute(select(BacktestPnLAttributionRecord)).scalars().all()
        assert session.execute(select(BacktestGreeksAttributionRecord)).scalars().all()
        assert session.execute(select(BacktestReconstructedTradeRecord)).scalars().all()
        assert session.execute(select(BacktestStrategyCycleRecord)).scalars().all()
        assert session.execute(select(BacktestReplaySnapshotRecord)).scalars().all()
        assert session.execute(select(BacktestEventOverlayRecord)).scalars().all()
        assert session.execute(select(BacktestArbitrationDecisionRecord)).scalars().all()
        assert session.execute(select(BacktestComparisonRunRecord)).scalars().all()
        assert session.execute(select(BacktestExportMetadataRecord)).scalars().all()
