"""Persistence and query services for Sprint 9B replay workspace and decision intelligence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256

from backend.database.dtos import (
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
    WorkspaceMetadataDTO,
)
from backend.database.repositories.replay_workspace import (
    DecisionExplanationQueryRepository,
    DecisionExplanationRepository,
    ExperimentComparisonRepository,
    ExperimentQueryRepository,
    ExperimentRepository,
    ReplayAnnotationRepository,
    ReplayBookmarkRepository,
    ReplayBranchQueryRepository,
    ReplayBranchRepository,
    ReplayCheckpointRepository,
    ReplayComparisonRepository,
    ReplayDiagnosticRepository,
    ReplayEventRepository,
    ReplayFilterRepository,
    ReplayReproducibilityReportRepository,
    ReplaySessionRepository,
    ReplayTimelineQueryRepository,
    WorkspaceMetadataRepository,
)
from backend.database.session import DatabaseSessionManager


class ReplayWorkspaceMutationError(RuntimeError):
    """Raised when replay workspace persistence invariants are violated."""


@dataclass(slots=True, frozen=True)
class ReplayEventDensityReadModel:
    session_id: str
    branch_id: str
    event_count: int
    span_seconds: float
    event_density: float


@dataclass(slots=True, frozen=True)
class ReplayComplexityReadModel:
    session_id: str
    branch_id: str
    unique_event_types: int
    branch_depth: int
    complexity_score: float


class ReplayWorkspacePersistenceService:
    def __init__(self, session_manager: DatabaseSessionManager) -> None:
        self.session_manager = session_manager

    def store_state(
        self,
        *,
        sessions: list[ReplaySessionDTO],
        branches: list[ReplayBranchDTO],
        checkpoints: list[ReplayCheckpointDTO],
        bookmarks: list[ReplayBookmarkDTO],
        events: list[ReplayEventDTO],
        annotations: list[ReplayAnnotationDTO],
        filters: list[ReplayFilterDTO],
        comparisons: list[ReplayComparisonDTO],
        diagnostics: list[ReplayDiagnosticDTO],
        reproducibility_reports: list[ReplayReproducibilityReportDTO],
        decision_explanations: list[DecisionExplanationDTO],
        experiments: list[ExperimentDTO],
        experiment_comparisons: list[ExperimentComparisonDTO],
        workspace_metadata: list[WorkspaceMetadataDTO],
    ) -> None:
        with self.session_manager.session_scope() as session:
            ReplaySessionRepository(session).upsert_rows(
                [
                    {
                        **{
                            key: value
                            for key, value in asdict(item).items()
                            if key != "metadata_json"
                        },
                        "metadata": item.metadata_json,
                    }
                    for item in sessions
                ]
            )
            ReplayBranchRepository(session).upsert_rows(
                [
                    {
                        **{
                            key: value
                            for key, value in asdict(item).items()
                            if key not in {"decision_delta_json", "metadata_json"}
                        },
                        "decision_delta": item.decision_delta_json,
                        "metadata": item.metadata_json,
                    }
                    for item in branches
                ]
            )
            ReplayCheckpointRepository(session).upsert_rows([asdict(item) for item in checkpoints])
            ReplayBookmarkRepository(session).upsert_rows([asdict(item) for item in bookmarks])
            ReplayEventRepository(session).upsert_rows([asdict(item) for item in events])
            ReplayAnnotationRepository(session).upsert_rows(
                [
                    {
                        **{
                            key: value
                            for key, value in asdict(item).items()
                            if key != "metadata_json"
                        },
                        "metadata": item.metadata_json,
                    }
                    for item in annotations
                ]
            )
            ReplayFilterRepository(session).upsert_rows([asdict(item) for item in filters])
            ReplayComparisonRepository(session).upsert_rows([asdict(item) for item in comparisons])
            ReplayDiagnosticRepository(session).upsert_rows([asdict(item) for item in diagnostics])
            ReplayReproducibilityReportRepository(session).upsert_rows(
                [asdict(item) for item in reproducibility_reports]
            )
            DecisionExplanationRepository(session).upsert_rows(
                [asdict(item) for item in decision_explanations]
            )
            ExperimentRepository(session).upsert_rows(
                [
                    {
                        **{
                            key: value
                            for key, value in asdict(item).items()
                            if key not in {"configuration_json", "metadata_json"}
                        },
                        "configuration_json": item.configuration_json,
                        "metadata": item.metadata_json,
                    }
                    for item in experiments
                ]
            )
            ExperimentComparisonRepository(session).upsert_rows(
                [asdict(item) for item in experiment_comparisons]
            )
            WorkspaceMetadataRepository(session).upsert_rows(
                [asdict(item) for item in workspace_metadata]
            )


class ReplayWorkspaceQueryService:
    def __init__(self, session_manager: DatabaseSessionManager) -> None:
        self.session_manager = session_manager

    def replay_timeline(self, session_id: str, branch_id: str) -> list[ReplayEventDTO]:
        with self.session_manager.session_scope() as session:
            rows = ReplayTimelineQueryRepository(session).by_branch(session_id, branch_id)
            return [
                ReplayEventDTO(
                    session_id=row.session_id,
                    branch_id=row.branch_id,
                    event_sequence=row.event_sequence,
                    event_timestamp=row.event_timestamp,
                    event_type=row.event_type,
                    severity=row.severity,
                    strategy_id=row.strategy_id,
                    symbol=row.symbol,
                    scenario_id=row.scenario_id,
                    policy_id=row.policy_id,
                    optimizer_id=row.optimizer_id,
                    tags=row.tags,
                    payload_json=row.payload_json,
                    event_checksum=row.event_checksum,
                )
                for row in rows
            ]

    def replay_branches(self, session_id: str) -> list[ReplayBranchDTO]:
        with self.session_manager.session_scope() as session:
            rows = ReplayBranchQueryRepository(session).by_session(session_id)
            return [
                ReplayBranchDTO(
                    session_id=row.session_id,
                    branch_id=row.branch_id,
                    parent_branch_id=row.parent_branch_id,
                    root_snapshot_id=row.root_snapshot_id,
                    decision_delta_json=row.decision_delta_json,
                    metadata_json=row.metadata_json,
                    created_at=row.created_at,
                )
                for row in rows
            ]

    def decision_explanations(
        self, session_id: str, branch_id: str
    ) -> list[DecisionExplanationDTO]:
        with self.session_manager.session_scope() as session:
            rows = DecisionExplanationQueryRepository(session).by_branch(session_id, branch_id)
            return [
                DecisionExplanationDTO(
                    session_id=row.session_id,
                    branch_id=row.branch_id,
                    explanation_id=row.explanation_id,
                    event_sequence=row.event_sequence,
                    decision_kind=row.decision_kind,
                    explanation_json=row.explanation_json,
                    created_at=row.created_at,
                )
                for row in rows
            ]

    def experiments(self) -> list[ExperimentDTO]:
        with self.session_manager.session_scope() as session:
            rows = ExperimentQueryRepository(session).all_experiments()
            return [
                ExperimentDTO(
                    experiment_id=row.experiment_id,
                    hypothesis=row.hypothesis,
                    configuration_json=row.configuration_json,
                    dataset_refs=row.dataset_refs,
                    strategy_set=row.strategy_set,
                    optimization_set=row.optimization_set,
                    scenario_set=row.scenario_set,
                    replay_set=row.replay_set,
                    notes=row.notes,
                    tags=row.tags,
                    version=row.version,
                    result_summary=row.result_summary,
                    metadata_json=row.metadata_json,
                    created_at=row.created_at,
                )
                for row in rows
            ]

    def replay_event_density(self, session_id: str, branch_id: str) -> ReplayEventDensityReadModel:
        timeline = self.replay_timeline(session_id, branch_id)
        if not timeline:
            return ReplayEventDensityReadModel(
                session_id=session_id,
                branch_id=branch_id,
                event_count=0,
                span_seconds=0.0,
                event_density=0.0,
            )
        first = timeline[0].event_timestamp
        last = timeline[-1].event_timestamp
        span_seconds = max((last - first).total_seconds(), 1.0)
        count = len(timeline)
        return ReplayEventDensityReadModel(
            session_id=session_id,
            branch_id=branch_id,
            event_count=count,
            span_seconds=span_seconds,
            event_density=count / span_seconds,
        )

    def replay_complexity(self, session_id: str, branch_id: str) -> ReplayComplexityReadModel:
        timeline = self.replay_timeline(session_id, branch_id)
        branches = self.replay_branches(session_id)
        by_id = {item.branch_id: item for item in branches}
        depth = 0
        cursor = by_id.get(branch_id)
        while cursor is not None and cursor.parent_branch_id:
            depth += 1
            cursor = by_id.get(cursor.parent_branch_id)
        event_types = {item.event_type for item in timeline}
        complexity = (len(event_types) * (1 + depth)) + (len(timeline) / 10.0) + (depth * 0.5)
        return ReplayComplexityReadModel(
            session_id=session_id,
            branch_id=branch_id,
            unique_event_types=len(event_types),
            branch_depth=depth,
            complexity_score=complexity,
        )


def deterministic_replay_workspace_checksum(
    *,
    events: list[ReplayEventDTO],
    explanations: list[DecisionExplanationDTO],
) -> str:
    payload = {
        "events": [
            {
                "session_id": row.session_id,
                "branch_id": row.branch_id,
                "event_sequence": row.event_sequence,
                "event_type": row.event_type,
                "event_checksum": row.event_checksum,
            }
            for row in sorted(events, key=lambda item: (item.branch_id, item.event_sequence))
        ],
        "explanations": [
            {
                "branch_id": row.branch_id,
                "event_sequence": row.event_sequence,
                "decision_kind": row.decision_kind,
            }
            for row in sorted(explanations, key=lambda item: (item.branch_id, item.event_sequence))
        ],
    }
    return sha256(repr(payload).encode("utf-8")).hexdigest()
