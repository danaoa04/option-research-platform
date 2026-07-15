"""Deterministic historical backtesting event loop foundation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from math import sqrt
from typing import Any

from .exceptions import StrategyLifecycleError
from .guards import NoLookAheadGuard
from .models import (
	AsOfPolicy,
	BacktestConfiguration,
	BacktestRunResult,
	BacktestStatus,
	BacktestWarning,
	CashLedgerEntry,
	DeterministicEvent,
	EventContext,
	EventType,
	FailedEvent,
	InformationSetAudit,
	LedgerRecord,
	LifecycleStatus,
	PortfolioSnapshot,
	PositionState,
	ReproducibilityMetadata,
	StrategyLifecycle,
)


@dataclass(slots=True)
class BacktestEngineState:
	open_positions: tuple[PositionState, ...] = ()
	closed_positions: tuple[PositionState, ...] = ()
	pending_order_intents: tuple[dict[str, Any], ...] = ()
	cash_balance: float = 0.0
	reserved_capital: float = 0.0
	realized_pnl: float = 0.0
	unrealized_pnl: float = 0.0
	accrued_fees: float = 0.0
	dividends: float = 0.0
	warnings: list[BacktestWarning] = field(default_factory=list)
	failed_events: list[FailedEvent] = field(default_factory=list)
	event_ledger: list[LedgerRecord] = field(default_factory=list)
	trade_ledger: list[LedgerRecord] = field(default_factory=list)
	cash_history: list[CashLedgerEntry] = field(default_factory=list)
	position_history: list[PositionState] = field(default_factory=list)
	snapshots: list[PortfolioSnapshot] = field(default_factory=list)
	greeks_history: list[tuple[datetime, dict[str, float]]] = field(default_factory=list)
	exposure_history: list[tuple[datetime, dict[str, float]]] = field(default_factory=list)


@dataclass(slots=True)
class BacktestingEngine:
	guard: NoLookAheadGuard

	def run(
		self,
		*,
		configuration: BacktestConfiguration,
		strategy: StrategyLifecycle,
		events: tuple[DeterministicEvent, ...],
		information_lookup: Any | None = None,
	) -> BacktestRunResult:
		started_at = datetime.now(tz=UTC)
		state = BacktestEngineState(
			cash_balance=configuration.initial_capital,
			reserved_capital=configuration.reserve_cash,
		)

		strategy.initialize(configuration=configuration)

		for event in events:
			try:
				self._process_event(
					state=state,
					strategy=strategy,
					event=event,
					configuration=configuration,
					information_lookup=information_lookup,
				)
			except Exception as exc:
				state.failed_events.append(
					FailedEvent(
						event_id=event.event_id,
						timestamp=event.timestamp,
						event_type=event.event_type,
						reason_code="event_failure",
						message=str(exc),
						recoverable=True,
					)
				)
				state.event_ledger.append(
					self._ledger(
						event=event,
						strategy_id=strategy.strategy_id,
						position_id=None,
						record_type="failure",
						reason_code="event_failure",
						payload={"error": str(exc)},
						software_version=configuration.software_git_commit,
					)
				)

		ended_at = datetime.now(tz=UTC)
		result = self._build_result(
			configuration=configuration,
			state=state,
			started_at=started_at,
			ended_at=ended_at,
		)
		strategy.finalize(result=result)
		return result

	def _process_event(
		self,
		*,
		state: BacktestEngineState,
		strategy: StrategyLifecycle,
		event: DeterministicEvent,
		configuration: BacktestConfiguration,
		information_lookup: Any | None,
	) -> None:
		information_set = self._information_set(event=event, lookup=information_lookup)
		snapshot = self._snapshot(state=state, timestamp=event.timestamp)
		context = EventContext(
			event=event,
			information_set=information_set,
			open_positions=state.open_positions,
			portfolio_snapshot=snapshot,
		)

		state.event_ledger.append(
			self._ledger(
				event=event,
				strategy_id=strategy.strategy_id,
				position_id=None,
				record_type="event",
				reason_code=event.event_type.value,
				payload=event.payload,
				software_version=configuration.software_git_commit,
			)
		)

		if event.event_type is EventType.LIFECYCLE_EVALUATION:
			self._handle_lifecycle(state=state, strategy=strategy, context=context)
		elif event.event_type in {
			EventType.ENTRY_EVALUATION,
			EventType.MANAGEMENT_EVALUATION,
			EventType.EXIT_EVALUATION,
			EventType.ROLL_EVALUATION,
			EventType.FILL_EVENT,
		}:
			self._handle_lifecycle(state=state, strategy=strategy, context=context)
		elif event.event_type is EventType.VALUATION:
			state.snapshots.append(snapshot)
			state.greeks_history.append((event.timestamp, dict(snapshot.portfolio_greeks)))
			state.exposure_history.append((event.timestamp, dict(snapshot.portfolio_exposure)))
		elif event.event_type is EventType.OPTION_EXPIRATION:
			self._handle_expiration(state=state, strategy=strategy, context=context)
		elif event.event_type is EventType.CORPORATE_ACTION:
			self._handle_corporate_action(state=state, strategy=strategy, context=context)
		elif event.event_type is EventType.RISK_EVENT:
			state.warnings.append(
				BacktestWarning(
					timestamp=event.timestamp,
					strategy_id=strategy.strategy_id,
					position_id=None,
					reason_code="risk_event",
					message="risk event processed",
					metadata=dict(event.payload),
				)
			)

		state.position_history.extend(state.open_positions)

	def _handle_lifecycle(
		self,
		*,
		state: BacktestEngineState,
		strategy: StrategyLifecycle,
		context: EventContext,
	) -> None:
		decision = strategy.evaluate_entry(context=context)
		if decision.should_open:
			position = strategy.create_position(context=context)
			if position is None:
				raise StrategyLifecycleError(
					"strategy returned should_open without creating a position"
				)
			state.open_positions = (*state.open_positions, position)
			state.trade_ledger.append(
				self._ledger(
					event=context.event,
					strategy_id=strategy.strategy_id,
					position_id=position.position_id,
					record_type="position_open",
					reason_code=decision.reason_code,
					payload={"metadata": decision.metadata},
					software_version=None,
				)
			)

		updated_positions: list[PositionState] = []
		newly_closed: list[PositionState] = []
		for position in state.open_positions:
			marked = strategy.mark_position(context=context, position=position)
			management = strategy.evaluate_management_rules(context=context, position=marked)
			exit_decision = strategy.evaluate_exit(context=context, position=marked)
			roll_decision = strategy.evaluate_roll_eligibility(context=context, position=marked)

			if management.should_close or exit_decision.should_close:
				closed = PositionState(
					position_id=marked.position_id,
					strategy_id=marked.strategy_id,
					lifecycle_status=LifecycleStatus.CLOSED,
					opened_at=marked.opened_at,
					closed_at=context.event.timestamp,
					legs=marked.legs,
					realized_pnl=marked.realized_pnl,
					unrealized_pnl=0.0,
					metadata=dict(marked.metadata),
				)
				newly_closed.append(closed)
				state.trade_ledger.append(
					self._ledger(
						event=context.event,
						strategy_id=strategy.strategy_id,
						position_id=marked.position_id,
						record_type="position_close",
						reason_code=exit_decision.reason_code,
						payload={
							"management_reason": management.reason_code,
							"roll_eligible": roll_decision.should_roll,
						},
						software_version=None,
					)
				)
				continue

			updated_positions.append(marked)

		state.open_positions = tuple(updated_positions)
		if newly_closed:
			state.closed_positions = (*state.closed_positions, *tuple(newly_closed))

	def _handle_expiration(
		self,
		*,
		state: BacktestEngineState,
		strategy: StrategyLifecycle,
		context: EventContext,
	) -> None:
		refreshed: list[PositionState] = []
		for position in state.open_positions:
			processed = strategy.process_expiration(context=context, position=position)
			refreshed.append(processed)

			state.event_ledger.append(
				self._ledger(
					event=context.event,
					strategy_id=strategy.strategy_id,
					position_id=position.position_id,
					record_type="expiration",
					reason_code="expiration_processing",
					payload={
						"exercise_style": [leg.exercise_style for leg in processed.legs],
						"settlement_pending": True,
					},
					software_version=None,
				)
			)
		state.open_positions = tuple(refreshed)

	def _handle_corporate_action(
		self,
		*,
		state: BacktestEngineState,
		strategy: StrategyLifecycle,
		context: EventContext,
	) -> None:
		state.event_ledger.append(
			self._ledger(
				event=context.event,
				strategy_id=strategy.strategy_id,
				position_id=None,
				record_type="corporate_action",
				reason_code="applied",
				payload={"raw": dict(context.event.payload)},
				software_version=None,
			)
		)

	def _information_set(
		self,
		*,
		event: DeterministicEvent,
		lookup: Any | None,
	) -> tuple[InformationSetAudit, ...]:
		if lookup is None:
			return (
				self.guard.audit_lookup(
					lookup_key="event_payload",
					requested_timestamp=event.timestamp,
					observed_timestamp=event.timestamp,
					as_of_policy=AsOfPolicy.EXACT,
					source_manifest=event.payload.get("manifest"),
					source_ref=event.payload.get("source_ref"),
					reason_code="event_time_snapshot",
					metadata={"event_type": event.event_type.value},
				),
			)

		payload = lookup(event.timestamp)
		records: list[InformationSetAudit] = []
		for item in payload:
			observed_ts = item.get("observed_timestamp")
			if isinstance(observed_ts, datetime):
				self.guard.assert_visible(as_of=event.timestamp, record_timestamp=observed_ts)
			records.append(
				self.guard.audit_lookup(
					lookup_key=str(item.get("lookup_key", "unknown")),
					requested_timestamp=event.timestamp,
					observed_timestamp=observed_ts if isinstance(observed_ts, datetime) else None,
					as_of_policy=AsOfPolicy(
						str(item.get("as_of_policy", AsOfPolicy.NEAREST_PRIOR))
					),
					source_manifest=item.get("source_manifest"),
					source_ref=item.get("source_ref"),
					reason_code=str(item.get("reason_code", "lookup")),
					metadata=dict(item.get("metadata", {})),
				)
			)
		return tuple(records)

	def _snapshot(self, *, state: BacktestEngineState, timestamp: datetime) -> PortfolioSnapshot:
		total_greeks = _aggregate_greeks(state.open_positions)
		return PortfolioSnapshot(
			timestamp=timestamp,
			cash_balance=state.cash_balance,
			reserved_capital=state.reserved_capital,
			realized_pnl=state.realized_pnl,
			unrealized_pnl=state.unrealized_pnl,
			accrued_fees=state.accrued_fees,
			dividends=state.dividends,
			portfolio_greeks=total_greeks,
			portfolio_exposure={"notional": state.reserved_capital},
			capital_utilization=(
				state.reserved_capital / max(1e-9, state.cash_balance + state.reserved_capital)
			),
		)

	def _ledger(
		self,
		*,
		event: DeterministicEvent,
		strategy_id: str,
		position_id: str | None,
		record_type: str,
		reason_code: str,
		payload: dict[str, Any],
		software_version: str | None,
	) -> LedgerRecord:
		checksum = sha256(
			f"{event.event_id}|{record_type}|{reason_code}|{sorted(payload.items())}".encode()
		).hexdigest()
		return LedgerRecord(
			timestamp=event.timestamp,
			strategy_id=strategy_id,
			position_id=position_id,
			record_type=record_type,
			reason_code=reason_code,
			sequence_number=event.sequence_number,
			payload=dict(payload),
			manifest_reference=event.payload.get("manifest"),
			software_version=software_version,
			checksum_metadata={"row_checksum": checksum},
		)

	def _build_result(
		self,
		*,
		configuration: BacktestConfiguration,
		state: BacktestEngineState,
		started_at: datetime,
		ended_at: datetime,
	) -> BacktestRunResult:
		equity_curve = tuple(
			(
				item.timestamp,
				item.cash_balance + item.realized_pnl + item.unrealized_pnl,
			)
			for item in state.snapshots
		)
		returns = _returns(equity_curve)
		max_drawdown = _max_drawdown(equity_curve)
		winners = [item for item in returns if item > 0]
		losers = [item for item in returns if item < 0]
		total_return = returns[-1] if returns else 0.0

		checksums = {
			"event_ledger": _checksum_records(state.event_ledger),
			"trade_ledger": _checksum_records(state.trade_ledger),
			"cash_history": _checksum_records(state.cash_history),
			"position_history": _checksum_records(state.position_history),
		}

		reproducibility = ReproducibilityMetadata(
			event_ordering="timestamp_priority_sequence",
			information_set_policy="no_look_ahead",
			lookup_policies={"default": "nearest_prior"},
			dataset_manifests=configuration.dataset_manifests,
			volatility_surface_snapshots=tuple(
				str(configuration.metadata.get("vol_surface_snapshot", ""))
				for _ in configuration.dataset_manifests
			),
			pricing_models=dict(configuration.metadata.get("pricing_models", {})),
			tree_step_policies=dict(configuration.metadata.get("tree_step_policies", {})),
			lifecycle_policies=dict(configuration.lifecycle_policies),
			fill_policies=dict(configuration.fill_model_config),
			scenario_policies=dict(configuration.metadata.get("scenario_policies", {})),
			software_git_commit=configuration.software_git_commit,
			schema_version=configuration.schema_version,
			deterministic_seed=configuration.random_seed,
			result_checksums=checksums,
		)

		return BacktestRunResult(
			configuration=configuration,
			status=BacktestStatus.FAILED if state.failed_events else BacktestStatus.COMPLETED,
			started_at=started_at,
			ended_at=ended_at,
			trade_ledger=tuple(state.trade_ledger),
			event_ledger=tuple(state.event_ledger),
			equity_curve=equity_curve,
			cash_history=tuple(state.cash_history),
			position_history=tuple((*state.position_history, *state.closed_positions)),
			greeks_history=tuple(state.greeks_history),
			exposure_history=tuple(state.exposure_history),
			realized_pnl=state.realized_pnl,
			unrealized_pnl=state.unrealized_pnl,
			total_return=total_return,
			cagr=_cagr(equity_curve, started_at, ended_at),
			sharpe=_sharpe(returns),
			sortino=_sortino(returns),
			maximum_drawdown=max_drawdown,
			expected_shortfall=_expected_shortfall(returns),
			win_rate=(len(winners) / len(returns)) if returns else 0.0,
			profit_factor=(sum(winners) / abs(sum(losers))) if losers else float("inf"),
			average_winner=(sum(winners) / len(winners)) if winners else 0.0,
			average_loser=(sum(losers) / len(losers)) if losers else 0.0,
			time_under_water_days=_time_under_water(equity_curve),
			capital_utilization=(
				state.reserved_capital / max(1e-9, state.cash_balance + state.reserved_capital)
			),
			warnings=tuple(state.warnings),
			failed_events=tuple(state.failed_events),
			reproducibility=reproducibility,
		)


def _aggregate_greeks(positions: tuple[PositionState, ...]) -> dict[str, float]:
	total = {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0}
	for position in positions:
		for leg in position.legs:
			total["delta"] += (leg.delta or 0.0) * leg.quantity
			total["gamma"] += (leg.gamma or 0.0) * leg.quantity
			total["theta"] += (leg.theta or 0.0) * leg.quantity
			total["vega"] += (leg.vega or 0.0) * leg.quantity
			total["rho"] += (leg.rho or 0.0) * leg.quantity
	return total


def _returns(equity_curve: tuple[tuple[datetime, float], ...]) -> list[float]:
	values = [value for _, value in equity_curve]
	if len(values) < 2:
		return []
	output: list[float] = []
	for idx in range(1, len(values)):
		previous = values[idx - 1]
		current = values[idx]
		if previous == 0:
			output.append(0.0)
		else:
			output.append((current / previous) - 1.0)
	return output


def _max_drawdown(equity_curve: tuple[tuple[datetime, float], ...]) -> float:
	peak = float("-inf")
	max_dd = 0.0
	for _, value in equity_curve:
		peak = max(peak, value)
		if peak <= 0:
			continue
		max_dd = max(max_dd, (peak - value) / peak)
	return max_dd


def _sharpe(returns: list[float]) -> float:
	if len(returns) < 2:
		return 0.0
	mean = sum(returns) / len(returns)
	variance = sum((item - mean) ** 2 for item in returns) / (len(returns) - 1)
	std = sqrt(max(variance, 1e-12))
	return mean / std


def _sortino(returns: list[float]) -> float:
	if len(returns) < 2:
		return 0.0
	mean = sum(returns) / len(returns)
	downside = [item for item in returns if item < 0]
	if not downside:
		return float("inf")
	downside_variance = sum(item * item for item in downside) / len(downside)
	downside_std = sqrt(max(downside_variance, 1e-12))
	return mean / downside_std


def _expected_shortfall(returns: list[float], alpha: float = 0.05) -> float:
	if not returns:
		return 0.0
	ordered = sorted(returns)
	count = max(1, int(len(ordered) * alpha))
	tail = ordered[:count]
	return -sum(tail) / len(tail)


def _cagr(
	equity_curve: tuple[tuple[datetime, float], ...],
	started_at: datetime,
	ended_at: datetime,
) -> float:
	if len(equity_curve) < 2:
		return 0.0
	start_value: float = float(equity_curve[0][1])
	end_value: float = float(equity_curve[-1][1])
	if start_value <= 0 or end_value <= 0:
		return 0.0
	years: float = max((ended_at - started_at).days / 365.25, 1e-9)
	growth: float = end_value / start_value
	return float((growth ** (1.0 / years)) - 1.0)


def _time_under_water(equity_curve: tuple[tuple[datetime, float], ...]) -> float:
	if not equity_curve:
		return 0.0
	peak = float("-inf")
	days = 0.0
	for idx, (timestamp, equity) in enumerate(equity_curve):
		peak = max(peak, equity)
		if equity >= peak:
			continue
		if idx == 0:
			continue
		previous_ts, _ = equity_curve[idx - 1]
		days += max(0.0, (timestamp - previous_ts).total_seconds() / 86400.0)
	return days


def _checksum_records(records: list[Any]) -> str:
	payload = repr([str(item) for item in records])
	return sha256(payload.encode("utf-8")).hexdigest()

