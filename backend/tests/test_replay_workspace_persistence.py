from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import create_engine

from backend.database import (
    DecisionExplanationDTO,
    ExperimentComparisonDTO,
    ExperimentDTO,
    ReplayAnnotationDTO,
    ReplayBookmarkDTO,
    ReplayBranchDTO,
    ReplayCheckpointDTO,
    ReplayComparisonDTO,
    ReplayDiagnosticDTO,
    ReplayEventDTO,
    ReplayFilterDTO,
    ReplayReproducibilityReportDTO,
    ReplaySessionDTO,
    ReplayWorkspacePersistenceService,
    ReplayWorkspaceQueryService,
    WorkspaceMetadataDTO,
    deterministic_replay_workspace_checksum,
)
from backend.database.models import Base
from backend.database.session import DatabaseSessionManager


def test_replay_workspace_round_trip_and_read_models() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    manager = DatabaseSessionManager(engine)
    persist = ReplayWorkspacePersistenceService(manager)
    query = ReplayWorkspaceQueryService(manager)

    ts = datetime(2026, 7, 3, 10, 0, tzinfo=UTC)

    session = ReplaySessionDTO(
        session_id="sess-1",
        run_id="run-1",
        timeline_id="tl-1",
        base_branch_id="main",
        status="active",
        metadata_json={"mode": "offline"},
        created_at=ts,
    )
    main_branch = ReplayBranchDTO(
        session_id="sess-1",
        branch_id="main",
        parent_branch_id=None,
        root_snapshot_id="snap-0",
        decision_delta_json={},
        metadata_json={"label": "main"},
        created_at=ts,
    )
    alt_branch = ReplayBranchDTO(
        session_id="sess-1",
        branch_id="alt-1",
        parent_branch_id="main",
        root_snapshot_id="snap-1",
        decision_delta_json={"policy": "conservative"},
        metadata_json={"label": "alt"},
        created_at=ts,
    )
    events = [
        ReplayEventDTO(
            session_id="sess-1",
            branch_id="main",
            event_sequence=0,
            event_timestamp=ts,
            event_type="entry",
            severity="info",
            strategy_id="s-1",
            symbol="SPY",
            scenario_id="shock-1",
            policy_id="risk-first",
            optimizer_id="opt-1",
            tags=["baseline"],
            payload_json={"delta": 0.2},
            event_checksum="chk-1",
        ),
        ReplayEventDTO(
            session_id="sess-1",
            branch_id="main",
            event_sequence=1,
            event_timestamp=ts,
            event_type="roll",
            severity="warning",
            strategy_id="s-1",
            symbol="SPY",
            scenario_id="shock-1",
            policy_id="risk-first",
            optimizer_id="opt-1",
            tags=["decision"],
            payload_json={"reason": "theta_decay"},
            event_checksum="chk-2",
        ),
    ]
    explanations = [
        DecisionExplanationDTO(
            session_id="sess-1",
            explanation_id="exp-1",
            branch_id="main",
            event_sequence=1,
            decision_kind="roll",
            explanation_json={"policy_score": 0.88},
            created_at=ts,
        )
    ]

    persist.store_state(
        sessions=[session],
        branches=[main_branch, alt_branch],
        checkpoints=[
            ReplayCheckpointDTO(
                session_id="sess-1",
                checkpoint_id="cp-1",
                branch_id="main",
                event_index=1,
                snapshot_id="snap-1",
                label="pre-roll",
                created_at=ts,
            )
        ],
        bookmarks=[
            ReplayBookmarkDTO(
                session_id="sess-1",
                bookmark_id="bm-1",
                branch_id="main",
                event_index=1,
                label="review",
                tags=["critical"],
                created_at=ts,
            )
        ],
        events=events,
        annotations=[
            ReplayAnnotationDTO(
                session_id="sess-1",
                annotation_id="an-1",
                branch_id="main",
                event_sequence=1,
                note_markdown="Risk policy preferred roll due to decay.",
                metadata_json={"author": "test"},
                created_at=ts,
            )
        ],
        filters=[
            ReplayFilterDTO(
                session_id="sess-1",
                filter_id="f-1",
                branch_id="main",
                filter_json={"event_types": ["roll"]},
                created_at=ts,
            )
        ],
        comparisons=[
            ReplayComparisonDTO(
                session_id="sess-1",
                comparison_id="cmp-1",
                left_branch_id="main",
                right_branch_id="alt-1",
                comparison_json={"pnl_delta": -12.0},
                created_at=ts,
            )
        ],
        diagnostics=[
            ReplayDiagnosticDTO(
                session_id="sess-1",
                diagnostic_id="diag-1",
                branch_id="main",
                diagnostic_json={"stale_quotes": 0},
                created_at=ts,
            )
        ],
        reproducibility_reports=[
            ReplayReproducibilityReportDTO(
                session_id="sess-1",
                report_id="rr-1",
                left_run_id="run-1",
                right_run_id="run-1",
                status="match",
                report_json={"differences": []},
                created_at=ts,
            )
        ],
        decision_explanations=explanations,
        experiments=[
            ExperimentDTO(
                experiment_id="expA",
                hypothesis="Conservative roll policy reduces drawdown.",
                configuration_json={"policy": "conservative"},
                dataset_refs=["manifest-1"],
                strategy_set=["calendar_v2"],
                optimization_set=["grid-v1"],
                scenario_set=["shock-1"],
                replay_set=["sess-1"],
                notes="offline deterministic",
                tags=["sprint9b"],
                version="1.0",
                result_summary={"drawdown": -0.04},
                metadata_json={"owner": "qa"},
                created_at=ts,
            )
        ],
        experiment_comparisons=[
            ExperimentComparisonDTO(
                comparison_id="excmp-1",
                left_experiment_id="expA",
                right_experiment_id="expA",
                comparison_json={"same": True},
                created_at=ts,
            )
        ],
        workspace_metadata=[
            WorkspaceMetadataDTO(
                workspace_key="default_layout",
                value_json={"panels": ["timeline", "details"]},
                created_at=ts,
            )
        ],
    )

    timeline = query.replay_timeline("sess-1", "main")
    assert len(timeline) == 2
    assert timeline[1].event_type == "roll"

    branches = query.replay_branches("sess-1")
    assert len(branches) == 2

    explanation_rows = query.decision_explanations("sess-1", "main")
    assert explanation_rows and explanation_rows[0].decision_kind == "roll"

    density = query.replay_event_density("sess-1", "main")
    assert density.event_count == 2
    assert density.event_density > 0.0

    complexity = query.replay_complexity("sess-1", "alt-1")
    assert complexity.branch_depth == 1
    assert complexity.complexity_score > 0.0

    experiments = query.experiments()
    assert len(experiments) == 1
    assert experiments[0].experiment_id == "expA"

    checksum = deterministic_replay_workspace_checksum(
        events=timeline,
        explanations=explanation_rows,
    )
    assert isinstance(checksum, str)
    assert len(checksum) == 64
