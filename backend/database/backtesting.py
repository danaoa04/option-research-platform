"""Persistence services for deterministic historical backtesting runs."""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256

from backend.database.dtos import (
	BacktestCashLedgerEntryDTO,
	BacktestEventDTO,
	BacktestIntegrityFailureDTO,
	BacktestLifecycleTriggerDTO,
	BacktestOrderIntentDTO,
	BacktestPartialFillDTO,
	BacktestPortfolioSnapshotDTO,
	BacktestPositionDTO,
	BacktestPositionInstanceDTO,
	BacktestPositionLegDTO,
	BacktestReconciliationEventDTO,
	BacktestReproducibilityChecksumDTO,
	BacktestResearchFillDTO,
	BacktestRollPlanDTO,
	BacktestRollRelationshipDTO,
	BacktestRunComparisonDTO,
	BacktestRunDTO,
	BacktestScenarioResultDTO,
	BacktestStateTransitionDTO,
	BacktestStrategyDefinitionDTO,
	BacktestStrategyHistoryDTO,
	BacktestStrategyInstanceDTO,
	BacktestStrategyTemplateDTO,
	BacktestTransitionGuardDTO,
	BacktestValuationDTO,
)
from backend.database.repositories.backtesting import (
	BacktestCashLedgerRepository,
	BacktestEventRepository,
	BacktestIntegrityFailureRepository,
	BacktestLifecycleTriggerRepository,
	BacktestOrderIntentRepository,
	BacktestPartialFillRepository,
	BacktestPortfolioSnapshotRepository,
	BacktestPositionInstanceRepository,
	BacktestPositionLegRepository,
	BacktestPositionRepository,
	BacktestReconciliationEventRepository,
	BacktestReproducibilityChecksumRepository,
	BacktestResearchFillRepository,
	BacktestRollPlanRepository,
	BacktestRollRelationshipRepository,
	BacktestRunComparisonRepository,
	BacktestRunRepository,
	BacktestScenarioResultRepository,
	BacktestStateTransitionRepository,
	BacktestStrategyDefinitionRepository,
	BacktestStrategyHistoryRepository,
	BacktestStrategyInstanceRepository,
	BacktestStrategyTemplateRepository,
	BacktestTransitionGuardRepository,
	BacktestValuationRepository,
)
from backend.database.session import DatabaseSessionManager


class BacktestMutationError(RuntimeError):
	"""Raised when backtest persistence invariants are violated."""


class BacktestPersistenceService:
	def __init__(self, session_manager: DatabaseSessionManager) -> None:
		self.session_manager = session_manager

	def store_run(
		self,
		run: BacktestRunDTO,
		*,
		events: list[BacktestEventDTO],
		order_intents: list[BacktestOrderIntentDTO],
		fills: list[BacktestResearchFillDTO],
		positions: list[BacktestPositionDTO],
		position_legs: list[BacktestPositionLegDTO],
		valuations: list[BacktestValuationDTO],
		cash_ledger: list[BacktestCashLedgerEntryDTO],
		snapshots: list[BacktestPortfolioSnapshotDTO],
		lifecycle_triggers: list[BacktestLifecycleTriggerDTO],
		run_comparisons: list[BacktestRunComparisonDTO],
		scenarios: list[BacktestScenarioResultDTO],
		reproducibility_checksums: list[BacktestReproducibilityChecksumDTO],
		strategy_definitions: list[BacktestStrategyDefinitionDTO] | None = None,
		strategy_templates: list[BacktestStrategyTemplateDTO] | None = None,
		strategy_instances: list[BacktestStrategyInstanceDTO] | None = None,
		position_instances: list[BacktestPositionInstanceDTO] | None = None,
		state_transitions: list[BacktestStateTransitionDTO] | None = None,
		transition_guards: list[BacktestTransitionGuardDTO] | None = None,
		roll_plans: list[BacktestRollPlanDTO] | None = None,
		roll_relationships: list[BacktestRollRelationshipDTO] | None = None,
		partial_fills: list[BacktestPartialFillDTO] | None = None,
		reconciliation_events: list[BacktestReconciliationEventDTO] | None = None,
		integrity_failures: list[BacktestIntegrityFailureDTO] | None = None,
		strategy_histories: list[BacktestStrategyHistoryDTO] | None = None,
	) -> int:
		strategy_definitions = strategy_definitions or []
		strategy_templates = strategy_templates or []
		strategy_instances = strategy_instances or []
		position_instances = position_instances or []
		state_transitions = state_transitions or []
		transition_guards = transition_guards or []
		roll_plans = roll_plans or []
		roll_relationships = roll_relationships or []
		partial_fills = partial_fills or []
		reconciliation_events = reconciliation_events or []
		integrity_failures = integrity_failures or []
		strategy_histories = strategy_histories or []

		self._validate_run(run)
		payload = {
			"run_id": run.run_id,
			"strategy_name": run.strategy_name,
			"started_at": run.started_at,
			"ended_at": run.ended_at,
			"configuration_json": run.configuration_json,
			"status": run.status,
			"reproducibility_json": run.reproducibility_json,
			"checksums": run.checksums,
			"metadata": run.metadata_json,
			"software_git_commit": run.software_git_commit,
			"schema_version": run.schema_version,
			"random_seed": run.random_seed,
			"created_at": run.created_at,
		}
		with self.session_manager.session_scope() as session:
			run_row_id = BacktestRunRepository(session).upsert_run(payload)

			BacktestEventRepository(session).insert_rows(
				[{"run_row_id": run_row_id, **asdict(item)} for item in events]
			)
			BacktestOrderIntentRepository(session).insert_rows(
				[
					{
						"run_row_id": run_row_id,
						**{k.replace("_json", ""): v for k, v in asdict(item).items()},
					}
					for item in order_intents
				]
			)
			BacktestResearchFillRepository(session).insert_rows(
				[{"run_row_id": run_row_id, **asdict(item)} for item in fills]
			)
			BacktestPositionRepository(session).insert_rows(
				[
					{
						"run_row_id": run_row_id,
						**{k.replace("_json", ""): v for k, v in asdict(item).items()},
					}
					for item in positions
				]
			)
			BacktestPositionLegRepository(session).insert_rows(
				[{"run_row_id": run_row_id, **asdict(item)} for item in position_legs]
			)
			BacktestValuationRepository(session).insert_rows(
				[{"run_row_id": run_row_id, **asdict(item)} for item in valuations]
			)
			BacktestCashLedgerRepository(session).insert_rows(
				[
					{
						"run_row_id": run_row_id,
						**{k.replace("_json", ""): v for k, v in asdict(item).items()},
					}
					for item in cash_ledger
				]
			)
			BacktestPortfolioSnapshotRepository(session).insert_rows(
				[{"run_row_id": run_row_id, **asdict(item)} for item in snapshots]
			)
			BacktestLifecycleTriggerRepository(session).insert_rows(
				[
					{
						"run_row_id": run_row_id,
						**{k.replace("_json", ""): v for k, v in asdict(item).items()},
					}
					for item in lifecycle_triggers
				]
			)
			BacktestRunComparisonRepository(session).insert_rows(
				[asdict(item) for item in run_comparisons]
			)
			BacktestScenarioResultRepository(session).insert_rows(
				[{"run_row_id": run_row_id, **asdict(item)} for item in scenarios]
			)
			BacktestReproducibilityChecksumRepository(session).insert_rows(
				[
					{
						"run_row_id": run_row_id,
						**{k.replace("_json", ""): v for k, v in asdict(item).items()},
					}
					for item in reproducibility_checksums
				]
			)
			BacktestStrategyDefinitionRepository(session).insert_rows(
				[
					{
						"run_row_id": run_row_id,
						**{
							key: value
							for key, value in asdict(item).items()
							if key != "metadata_json"
						},
						"metadata": item.metadata_json,
					}
					for item in strategy_definitions
				]
			)
			BacktestStrategyTemplateRepository(session).insert_rows(
				[
					{
						"run_row_id": run_row_id,
						**{
							key: value
							for key, value in asdict(item).items()
							if key != "metadata_json"
						},
						"metadata": item.metadata_json,
					}
					for item in strategy_templates
				]
			)
			BacktestStrategyInstanceRepository(session).insert_rows(
				[
					{
						"run_row_id": run_row_id,
						**{
							key: value
							for key, value in asdict(item).items()
							if key != "metadata_json"
						},
						"metadata": item.metadata_json,
					}
					for item in strategy_instances
				]
			)
			BacktestPositionInstanceRepository(session).insert_rows(
				[
					{
						"run_row_id": run_row_id,
						**{
							key: value
							for key, value in asdict(item).items()
							if key != "metadata_json"
						},
						"metadata": item.metadata_json,
					}
					for item in position_instances
				]
			)
			BacktestStateTransitionRepository(session).insert_rows(
				[
					{
						"run_row_id": run_row_id,
						**asdict(item),
					}
					for item in state_transitions
				]
			)
			BacktestTransitionGuardRepository(session).insert_rows(
				[
					{
						"run_row_id": run_row_id,
						**{k.replace("_json", ""): v for k, v in asdict(item).items()},
					}
					for item in transition_guards
				]
			)
			BacktestRollPlanRepository(session).insert_rows(
				[
					{
						"run_row_id": run_row_id,
						**asdict(item),
					}
					for item in roll_plans
				]
			)
			BacktestRollRelationshipRepository(session).insert_rows(
				[
					{
						"run_row_id": run_row_id,
						**asdict(item),
					}
					for item in roll_relationships
				]
			)
			BacktestPartialFillRepository(session).insert_rows(
				[
					{
						"run_row_id": run_row_id,
						**{
							key: value
							for key, value in asdict(item).items()
							if key != "metadata_json"
						},
						"metadata": item.metadata_json,
					}
					for item in partial_fills
				]
			)
			BacktestReconciliationEventRepository(session).insert_rows(
				[
					{
						"run_row_id": run_row_id,
						**asdict(item),
					}
					for item in reconciliation_events
				]
			)
			BacktestIntegrityFailureRepository(session).insert_rows(
				[
					{
						"run_row_id": run_row_id,
						**asdict(item),
					}
					for item in integrity_failures
				]
			)
			BacktestStrategyHistoryRepository(session).insert_rows(
				[
					{
						"run_row_id": run_row_id,
						**asdict(item),
					}
					for item in strategy_histories
				]
			)
			return run_row_id

	def _validate_run(self, run: BacktestRunDTO) -> None:
		required = {
			"event_ordering",
			"information_set_policy",
			"lookup_policies",
			"dataset_manifests",
			"fill_policies",
			"lifecycle_policies",
		}
		missing = sorted(required.difference(run.reproducibility_json))
		if missing:
			raise BacktestMutationError(
				f"backtest run missing reproducibility metadata: missing={missing}"
			)


def deterministic_backtest_run_checksum(
	*,
	run: BacktestRunDTO,
	events: list[BacktestEventDTO],
) -> str:
	payload = {
		"run_id": run.run_id,
		"status": run.status,
		"strategy_name": run.strategy_name,
		"started_at": run.started_at.isoformat(),
		"ended_at": run.ended_at.isoformat() if run.ended_at is not None else None,
		"event_sequence": [
			{
				"sequence_number": item.sequence_number,
				"event_type": item.event_type,
				"event_timestamp": item.event_timestamp.isoformat(),
			}
			for item in sorted(events, key=lambda row: row.sequence_number)
		],
		"checksums": run.checksums,
	}
	return sha256(repr(payload).encode("utf-8")).hexdigest()


__all__ = [
	"BacktestMutationError",
	"BacktestPersistenceService",
	"deterministic_backtest_run_checksum",
]
