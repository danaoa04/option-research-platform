from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest

from backend.database import (
    DecisionExplanationDTO,
    ReplayEventDTO,
    deterministic_replay_workspace_checksum,
)


@pytest.mark.skipif(
    os.getenv("RUN_REPLAY_WORKSPACE_BENCHMARKS") != "1",
    reason="opt-in replay workspace benchmark suite is disabled by default",
)
def test_replay_workspace_checksum_benchmark() -> None:
    ts = datetime(2026, 7, 2, 10, 0, tzinfo=UTC)
    events = [
        ReplayEventDTO(
            session_id="sess-1",
            branch_id="main",
            event_sequence=i,
            event_timestamp=ts,
            event_type="signal",
            severity="info",
            strategy_id="s-1",
            symbol="SPY",
            scenario_id=None,
            policy_id=None,
            optimizer_id=None,
            tags=["bench"],
            payload_json={"i": i},
            event_checksum=f"chk-{i}",
        )
        for i in range(1000)
    ]
    explanations = [
        DecisionExplanationDTO(
            session_id="sess-1",
            explanation_id=f"e-{i}",
            branch_id="main",
            event_sequence=i,
            decision_kind="hold",
            explanation_json={"score": 1.0},
            created_at=ts,
        )
        for i in range(1000)
    ]

    checksum = deterministic_replay_workspace_checksum(
        events=events,
        explanations=explanations,
    )
    assert isinstance(checksum, str)
    assert len(checksum) == 64
