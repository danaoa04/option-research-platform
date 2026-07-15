from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select

from backend.database import (
	BacktestEventDTO,
	BacktestPersistenceService,
	BacktestRunDTO,
	deterministic_backtest_run_checksum,
)
from backend.database.models import BacktestEventRecord, BacktestRun, Base
from backend.database.session import DatabaseSessionManager


def _run() -> BacktestRunDTO:
	timestamp = datetime(2026, 6, 2, 14, 30, tzinfo=UTC)
	return BacktestRunDTO(
		run_id="bt-run-1",
		strategy_name="calendar_spread",
		started_at=timestamp,
		ended_at=timestamp,
		configuration_json={"symbols": ["SPY"]},
		status="completed",
		reproducibility_json={
			"event_ordering": "timestamp_priority_sequence",
			"information_set_policy": "no_look_ahead",
			"lookup_policies": {"quotes": "nearest_prior"},
			"dataset_manifests": ["manifest-1"],
			"fill_policies": {"mode": "midpoint"},
			"lifecycle_policies": {"profit_target": 0.2},
		},
		checksums={"events": "abc"},
		metadata_json={"note": "fixture"},
		software_git_commit="deadbeef",
		schema_version="6.0",
		random_seed=7,
		created_at=timestamp,
	)


def test_backtest_persistence_round_trip() -> None:
	engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
	Base.metadata.create_all(engine)
	manager = DatabaseSessionManager(engine)
	service = BacktestPersistenceService(manager)
	run = _run()

	row_id = service.store_run(
		run,
		events=[
			BacktestEventDTO(
				sequence_number=1,
				event_timestamp=datetime(2026, 6, 2, 14, 30, tzinfo=UTC),
				event_type="session_open",
				priority=10,
				payload={"symbol": "SPY"},
				reason_code="session_open",
				strategy_id="calendar-spread",
				position_id=None,
				manifest_reference="manifest-1",
				software_version="deadbeef",
				checksum_metadata={"row": "1"},
			)
		],
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
	)

	with manager.session_scope() as session:
		stored_run = session.execute(select(BacktestRun)).scalars().one()
		stored_events = session.execute(select(BacktestEventRecord)).scalars().all()

	assert row_id == stored_run.id
	assert stored_run.run_id == run.run_id
	assert [item.event_type for item in stored_events] == ["session_open"]


def test_backtest_checksum_is_order_stable() -> None:
	run = _run()
	first = [
		BacktestEventDTO(
			sequence_number=2,
			event_timestamp=datetime(2026, 6, 2, 15, 0, tzinfo=UTC),
			event_type="quote",
			priority=20,
			payload={},
			reason_code="quote",
			strategy_id="s",
			position_id=None,
			manifest_reference=None,
			software_version=None,
			checksum_metadata={},
		),
		BacktestEventDTO(
			sequence_number=1,
			event_timestamp=datetime(2026, 6, 2, 14, 30, tzinfo=UTC),
			event_type="session_open",
			priority=10,
			payload={},
			reason_code="open",
			strategy_id="s",
			position_id=None,
			manifest_reference=None,
			software_version=None,
			checksum_metadata={},
		),
	]
	second = list(reversed(first))

	checksum_a = deterministic_backtest_run_checksum(run=run, events=first)
	checksum_b = deterministic_backtest_run_checksum(run=run, events=second)
	assert checksum_a == checksum_b


def test_alembic_upgrade_and_downgrade_for_0007_to_0010(tmp_path: Path) -> None:
	db_path = tmp_path / "migration_test.db"
	cfg = Config()
	cfg.set_main_option(
		"script_location",
		str(Path(__file__).resolve().parents[1] / "database" / "migrations"),
	)
	cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

	command.stamp(cfg, "0006_validation_foundation")
	command.upgrade(cfg, "0007_portfolio_selection_foundation")
	command.downgrade(cfg, "0006_validation_foundation")

	command.stamp(cfg, "0007_portfolio_selection_foundation")
	command.upgrade(cfg, "0008_backtesting_event_loop_foundation")

	engine = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
	with engine.connect() as conn:
		run_count = conn.exec_driver_sql("SELECT COUNT(*) FROM backtest_runs").scalar_one()
		assert run_count == 0
		conn.exec_driver_sql(
			"INSERT INTO backtest_runs ("
			"run_id, strategy_name, started_at, ended_at, configuration_json, status, "
			"reproducibility_json, checksums, metadata, software_git_commit, schema_version, "
			"random_seed, created_at"
			") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
			(
				"bt-run-migration",
				"calendar",
				"2026-06-02T14:30:00+00:00",
				"2026-06-02T14:30:00+00:00",
				"{}",
				"completed",
				"{}",
				"{}",
				"{}",
				"deadbeef",
				"6.0",
				7,
				"2026-06-02T14:30:00+00:00",
			),
		)
	engine.dispose()

	command.downgrade(cfg, "0007_portfolio_selection_foundation")

	command.stamp(cfg, "0008_backtesting_event_loop_foundation")
	command.upgrade(cfg, "0009_strategy_state_machine_foundation")

	engine_s6b = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
	with engine_s6b.connect() as conn:
		row_count = conn.exec_driver_sql(
			"SELECT COUNT(*) FROM backtest_strategy_instances"
		).scalar_one()
		assert row_count == 0
	engine_s6b.dispose()

	command.stamp(cfg, "0009_strategy_state_machine_foundation")
	command.upgrade(cfg, "0010_backtest_analytics_replay_foundation")

	engine_s6c = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
	with engine_s6c.connect() as conn:
		s6c_count = conn.exec_driver_sql(
			"SELECT COUNT(*) FROM backtest_strategy_analytics"
		).scalar_one()
		assert s6c_count == 0
		conn.exec_driver_sql(
			"INSERT INTO backtest_strategy_analytics ("
			"run_row_id, strategy_instance_id, snapshot_timestamp, realized_pnl, "
			"unrealized_pnl, total_pnl, return_value, capital_usage, cash_usage, "
			"intrinsic_value, extrinsic_value, greeks, implied_volatility, "
			"realized_volatility, iv_rank, iv_percentile, term_structure_json, "
			"liquidity_json, lifecycle_state, warnings, failures"
			") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
			(
				1,
				"si-1",
				"2026-06-02T14:30:00+00:00",
				0,
				0,
				0,
				0,
				0,
				0,
				0,
				0,
				"{}",
				None,
				None,
				None,
				None,
				"{}",
				"{}",
				"open",
				"[]",
				"[]",
			),
		)
	engine_s6c.dispose()

	command.downgrade(cfg, "0009_strategy_state_machine_foundation")

	engine_after_s6c = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
	with engine_after_s6c.connect() as conn:
		rows_s6c = conn.exec_driver_sql(
			"SELECT name FROM sqlite_master WHERE type='table' "
			"AND name='backtest_strategy_analytics'"
		).fetchall()
	engine_after_s6c.dispose()
	assert rows_s6c == []

	command.downgrade(cfg, "0008_backtesting_event_loop_foundation")

	engine_after_s6b = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
	with engine_after_s6b.connect() as conn:
		rows_s6b = conn.exec_driver_sql(
			"SELECT name FROM sqlite_master WHERE type='table' "
			"AND name='backtest_strategy_instances'"
		).fetchall()
	engine_after_s6b.dispose()
	assert rows_s6b == []

	engine_after = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
	with engine_after.connect() as conn:
		rows = conn.exec_driver_sql(
			"SELECT name FROM sqlite_master WHERE type='table' AND name='backtest_runs'"
		).fetchall()
	engine_after.dispose()
	assert rows == []
