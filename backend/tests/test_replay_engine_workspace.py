from __future__ import annotations

from datetime import UTC, datetime

from backend.backtesting.models import DeterministicEvent, EventType
from backend.backtesting.replay import BacktestReplayEngine, ReplayFilter


def _event(seq: int, event_type: EventType) -> DeterministicEvent:
    ts = datetime(2026, 7, 1, 10, seq, tzinfo=UTC)
    return DeterministicEvent(
        event_id=f"ev-{seq}",
        timestamp=ts,
        event_type=event_type,
        priority=10,
        sequence_number=seq,
        payload={"sequence": seq},
    )


def test_replay_engine_workspace_branching_and_checksum() -> None:
    engine = BacktestReplayEngine(
        events=(_event(0, EventType.ENTRY_EVALUATION), _event(1, EventType.FILL_EVENT))
    )

    session = engine.initialize_session(
        session_id="sess-1",
        run_id="run-1",
        timeline_id="tl-1",
    )
    assert session.base_branch_id == "main"

    engine.append_branch_event(
        branch_id="main",
        event_type="entry",
        severity="info",
        strategy_id="s-1",
        symbol="SPY",
        timestamp=datetime(2026, 7, 1, 10, 0, tzinfo=UTC),
        tags=("baseline",),
        payload={"action": "open"},
    )

    branch = engine.create_branch(
        branch_id="alt-1",
        parent_branch_id="main",
        root_snapshot_id="snap-1",
        decision_delta={"policy": "conservative"},
    )
    assert branch.parent_branch_id == "main"

    engine.append_branch_event(
        branch_id="alt-1",
        event_type="roll",
        severity="warning",
        strategy_id="s-1",
        symbol="SPY",
        timestamp=datetime(2026, 7, 1, 10, 1, tzinfo=UTC),
        tags=("decision",),
        payload={"reason": "theta_decay"},
    )

    timeline = engine.branch_timeline("alt-1")
    assert len(timeline) == 2

    checksum = engine.deterministic_branch_checksum("alt-1")
    assert isinstance(checksum, str)
    assert len(checksum) == 64


def test_replay_filter_explanations_and_immutable_snapshots() -> None:
    engine = BacktestReplayEngine(events=(_event(0, EventType.ENTRY_EVALUATION),))
    engine.initialize_session(session_id="sess-1", run_id="run-1", timeline_id="tl-1")
    engine.append_branch_event(
        branch_id="main",
        event_type="policy_evaluation",
        severity="info",
        strategy_id="s-1",
        symbol="SPY",
        timestamp=datetime(2026, 7, 1, 10, 0, tzinfo=UTC),
        tags=("entry",),
        payload={"policy_id": "entry-v1", "nested": {"score": 0.8}},
    )
    filtered = engine.filter_timeline(ReplayFilter(policy_id="entry-v1", user_tags=("entry",)))
    assert len(filtered) == 1

    state = {"positions": [{"symbol": "SPY"}]}
    snapshot = engine.create_snapshot(
        snapshot_id="snap-1",
        strategy_state={},
        leg_state={},
        portfolio_state=state,
        cash_state={},
        greeks={},
        volatility_state={},
        open_order_intents=(),
        pending_fills=(),
        lifecycle_state="open",
        source_checksums={},
    )
    assert snapshot is not None
    state["positions"][0]["symbol"] = "QQQ"
    assert snapshot.portfolio_state["positions"][0]["symbol"] == "SPY"

    explanation = engine.explain_decision(
        decision_kind="entry",
        outcome="approved",
        policy_id="entry-v1",
        reasons=({"code": "iv_rank", "observed": 54, "threshold": 40, "comparison": ">"},),
    )
    assert explanation.reasons[0]["passed"]
    assert len(engine.decision_graph("main").edges) == 6
