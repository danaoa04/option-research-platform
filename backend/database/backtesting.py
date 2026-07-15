"""Persistence services for deterministic historical backtesting runs."""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256

from backend.database.dtos import (
	BacktestArbitrationDecisionDTO,
	BacktestCashLedgerEntryDTO,
	BacktestComparisonRunDTO,
	BacktestEventDTO,
	BacktestEventOverlayDTO,
	BacktestExportMetadataDTO,
	BacktestGreeksAttributionDTO,
	BacktestIntegrityFailureDTO,
	BacktestLifecycleTriggerDTO,
	BacktestOrderIntentDTO,
	BacktestPartialFillDTO,
	BacktestPnLAttributionDTO,
	BacktestPortfolioAnalyticsDTO,
	BacktestPortfolioSnapshotDTO,
	BacktestPositionDTO,
	BacktestPositionInstanceDTO,
	BacktestPositionLegDTO,
	BacktestReconciliationEventDTO,
	BacktestReconstructedTradeDTO,
	BacktestReplaySnapshotDTO,
	BacktestReproducibilityChecksumDTO,
	BacktestResearchFillDTO,
	BacktestRollPlanDTO,
	BacktestRollRelationshipDTO,
	BacktestRunComparisonDTO,
	BacktestRunDTO,
	BacktestScenarioResultDTO,
	BacktestStateTransitionDTO,
	BacktestStrategyAnalyticsDTO,
	BacktestStrategyCycleDTO,
	BacktestStrategyDefinitionDTO,
	BacktestStrategyHistoryDTO,
	BacktestStrategyInstanceDTO,
	BacktestStrategyTemplateDTO,
	BacktestTransitionGuardDTO,
	BacktestValuationDTO,
)
from backend.database.repositories.backtesting import (
	BacktestArbitrationDecisionRepository,
	BacktestCashLedgerRepository,
	BacktestComparisonRunRepository,
	BacktestEventOverlayRepository,
	BacktestEventRepository,
	BacktestExportMetadataRepository,
	BacktestGreeksAttributionRepository,
	BacktestIntegrityFailureRepository,
	BacktestLifecycleTriggerRepository,
	BacktestOrderIntentRepository,
	BacktestPartialFillRepository,
	BacktestPnLAttributionRepository,
	BacktestPortfolioAnalyticsRepository,
	BacktestPortfolioSnapshotRepository,
	BacktestPositionInstanceRepository,
	BacktestPositionLegRepository,
	BacktestPositionRepository,
	BacktestReconciliationEventRepository,
	BacktestReconstructedTradeRepository,
	BacktestReplaySnapshotRepository,
	BacktestReproducibilityChecksumRepository,
	BacktestResearchFillRepository,
	BacktestRollPlanRepository,
	BacktestRollRelationshipRepository,
	BacktestRunComparisonRepository,
	BacktestRunRepository,
	BacktestScenarioResultRepository,
	BacktestStateTransitionRepository,
	BacktestStrategyAnalyticsRepository,
	BacktestStrategyCycleRepository,
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
		strategy_analytics: list[BacktestStrategyAnalyticsDTO] | None = None,
		portfolio_analytics: list[BacktestPortfolioAnalyticsDTO] | None = None,
		pnl_attributions: list[BacktestPnLAttributionDTO] | None = None,
		greeks_attributions: list[BacktestGreeksAttributionDTO] | None = None,
		reconstructed_trades: list[BacktestReconstructedTradeDTO] | None = None,
		strategy_cycles: list[BacktestStrategyCycleDTO] | None = None,
		replay_snapshots: list[BacktestReplaySnapshotDTO] | None = None,
		event_overlays: list[BacktestEventOverlayDTO] | None = None,
		arbitration_decisions: list[BacktestArbitrationDecisionDTO] | None = None,
		comparison_runs: list[BacktestComparisonRunDTO] | None = None,
		export_metadata: list[BacktestExportMetadataDTO] | None = None,
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
		strategy_analytics = strategy_analytics or []
		portfolio_analytics = portfolio_analytics or []
		pnl_attributions = pnl_attributions or []
		greeks_attributions = greeks_attributions or []
		reconstructed_trades = reconstructed_trades or []
		strategy_cycles = strategy_cycles or []
		replay_snapshots = replay_snapshots or []
		event_overlays = event_overlays or []
		arbitration_decisions = arbitration_decisions or []
		comparison_runs = comparison_runs or []
		export_metadata = export_metadata or []

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
			BacktestStrategyAnalyticsRepository(session).insert_rows(
				[
					{
						"run_row_id": run_row_id,
						**asdict(item),
					}
					for item in strategy_analytics
				]
			)
			BacktestPortfolioAnalyticsRepository(session).insert_rows(
				[
					{
						"run_row_id": run_row_id,
						**asdict(item),
					}
					for item in portfolio_analytics
				]
			)
			BacktestPnLAttributionRepository(session).insert_rows(
				[
					{
						"run_row_id": run_row_id,
						**asdict(item),
					}
					for item in pnl_attributions
				]
			)
			BacktestGreeksAttributionRepository(session).insert_rows(
				[
					{
						"run_row_id": run_row_id,
						**asdict(item),
					}
					for item in greeks_attributions
				]
			)
			BacktestReconstructedTradeRepository(session).insert_rows(
				[
					{
						"run_row_id": run_row_id,
						**asdict(item),
					}
					for item in reconstructed_trades
				]
			)
			BacktestStrategyCycleRepository(session).insert_rows(
				[
					{
						"run_row_id": run_row_id,
						**asdict(item),
					}
					for item in strategy_cycles
				]
			)
			BacktestReplaySnapshotRepository(session).insert_rows(
				[
					{
						"run_row_id": run_row_id,
						**asdict(item),
					}
					for item in replay_snapshots
				]
			)
			BacktestEventOverlayRepository(session).insert_rows(
				[
					{
						"run_row_id": run_row_id,
						**asdict(item),
					}
					for item in event_overlays
				]
			)
			BacktestArbitrationDecisionRepository(session).insert_rows(
				[
					{
						"run_row_id": run_row_id,
						**asdict(item),
					}
					for item in arbitration_decisions
				]
			)
			BacktestComparisonRunRepository(session).insert_rows(
				[
					{
						"run_row_id": run_row_id,
						**asdict(item),
					}
					for item in comparison_runs
				]
			)
			BacktestExportMetadataRepository(session).insert_rows(
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
					for item in export_metadata
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
