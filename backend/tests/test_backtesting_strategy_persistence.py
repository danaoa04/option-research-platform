from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import create_engine, select

from backend.database import (
    BacktestPersistenceService,
    BacktestPositionInstanceDTO,
    BacktestRunDTO,
    BacktestStateTransitionDTO,
    BacktestStrategyDefinitionDTO,
    BacktestStrategyInstanceDTO,
)
from backend.database.models import (
    BacktestPositionInstanceRecord,
    BacktestStateTransitionRecord,
    BacktestStrategyDefinitionRecord,
    BacktestStrategyInstanceRecord,
    Base,
)
from backend.database.session import DatabaseSessionManager


def test_strategy_state_machine_persistence_round_trip() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    manager = DatabaseSessionManager(engine)
    service = BacktestPersistenceService(manager)
    timestamp = datetime(2026, 6, 3, 14, 30, tzinfo=UTC)

    run = BacktestRunDTO(
        run_id="bt-s6b-1",
        strategy_name="pmcc",
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
        metadata_json={"sprint": "6B"},
        software_git_commit="deadbeef",
        schema_version="6.1",
        random_seed=11,
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
        strategy_definitions=[
            BacktestStrategyDefinitionDTO(
                definition_id="def-1",
                strategy_name="pmcc",
                definition_json={"legs": 2},
                validation_json={"valid": True},
                metadata_json={"template": "pmcc"},
            )
        ],
        strategy_instances=[
            BacktestStrategyInstanceDTO(
                strategy_instance_id="si-1",
                strategy_id="pmcc-1",
                definition_id="def-1",
                lifecycle_state="open",
                state_reason="entry_complete",
                as_of_timestamp=timestamp,
                metadata_json={"capital_usage": "moderate"},
            )
        ],
        position_instances=[
            BacktestPositionInstanceDTO(
                strategy_instance_id="si-1",
                position_instance_id="pi-1",
                lifecycle_state="open",
                opened_at=timestamp,
                closed_at=None,
                as_of_timestamp=timestamp,
                metadata_json={"net_debit": str(Decimal("1000"))},
            )
        ],
        state_transitions=[
            BacktestStateTransitionDTO(
                strategy_instance_id="si-1",
                position_instance_id="pi-1",
                sequence_number=1,
                transition_timestamp=timestamp,
                prior_state="entry_pending",
                next_state="open",
                trigger="fill_reconciliation",
                action_plan={"actions": ["activate_position"]},
                data_snapshot_reference="snap-1",
                software_git_commit="deadbeef",
                warnings=[],
                failures=[],
                checksum_metadata={"row_checksum": "xyz"},
            )
        ],
    )

    with manager.session_scope() as session:
        defs = session.execute(select(BacktestStrategyDefinitionRecord)).scalars().all()
        instances = session.execute(select(BacktestStrategyInstanceRecord)).scalars().all()
        positions = session.execute(select(BacktestPositionInstanceRecord)).scalars().all()
        transitions = session.execute(select(BacktestStateTransitionRecord)).scalars().all()

    assert len(defs) == 1
    assert len(instances) == 1
    assert len(positions) == 1
    assert len(transitions) == 1
