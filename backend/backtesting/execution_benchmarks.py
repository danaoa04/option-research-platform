"""Opt-in deterministic benchmarks for Sprint 7C execution calibration workflows."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter

from .execution_calibration import (
    ExecutionAction,
    ExecutionCalibrationRecord,
    ExecutionOrderType,
    ExecutionSide,
    ExecutionSourceType,
    ExecutionStressTestEngine,
    FillQualityAnalyzer,
    LiquidityRegime,
    MarketRegime,
    PartialFillCalibrator,
    SlippageCalibrator,
    SlippageModelKind,
    SpreadCaptureCalibrator,
    TransactionCostEngine,
    VolatilityRegime,
)


@dataclass(slots=True, frozen=True)
class ExecutionBenchmarkResult:
    name: str
    input_size: int
    elapsed_seconds: float


@dataclass(slots=True)
class ExecutionBenchmarkRunner:
    def run_all(self) -> list[ExecutionBenchmarkResult]:
        if os.getenv("RUN_EXECUTION_BENCHMARKS", "0") != "1":
            return []
        records = _records(2000)
        return [
            self._benchmark_fill_quality(records),
            self._benchmark_slippage_calibration(records),
            self._benchmark_spread_capture(records),
            self._benchmark_partial_fill(records),
            self._benchmark_transaction_cost(records),
            self._benchmark_stress_test(records),
        ]

    def _benchmark_fill_quality(
        self,
        records: tuple[ExecutionCalibrationRecord, ...],
    ) -> ExecutionBenchmarkResult:
        analyzer = FillQualityAnalyzer()
        start = perf_counter()
        _ = [
            analyzer.measure(
                record=item,
                arrival_price=item.request_price,
                timeout=False,
            )
            for item in records
        ]
        elapsed = perf_counter() - start
        return ExecutionBenchmarkResult("fill_quality_metrics", len(records), elapsed)

    def _benchmark_slippage_calibration(
        self,
        records: tuple[ExecutionCalibrationRecord, ...],
    ) -> ExecutionBenchmarkResult:
        start = perf_counter()
        _ = SlippageCalibrator(minimum_sample_size=10).calibrate(
            records=records,
            model=SlippageModelKind.SPREAD_WIDTH_DEPENDENT,
        )
        elapsed = perf_counter() - start
        return ExecutionBenchmarkResult("slippage_calibration", len(records), elapsed)

    def _benchmark_spread_capture(
        self,
        records: tuple[ExecutionCalibrationRecord, ...],
    ) -> ExecutionBenchmarkResult:
        start = perf_counter()
        _ = SpreadCaptureCalibrator(minimum_sample_size=10).calibrate(records=records)
        elapsed = perf_counter() - start
        return ExecutionBenchmarkResult("spread_capture_calibration", len(records), elapsed)

    def _benchmark_partial_fill(
        self,
        records: tuple[ExecutionCalibrationRecord, ...],
    ) -> ExecutionBenchmarkResult:
        start = perf_counter()
        _ = PartialFillCalibrator(minimum_sample_size=10).calibrate(
            records=records,
            strategy_complexity=2,
            legs=4,
            execution_policy="sequential",
        )
        elapsed = perf_counter() - start
        return ExecutionBenchmarkResult("partial_fill_calibration", len(records), elapsed)

    def _benchmark_transaction_cost(
        self,
        records: tuple[ExecutionCalibrationRecord, ...],
    ) -> ExecutionBenchmarkResult:
        start = perf_counter()
        _ = TransactionCostEngine().aggregate(records=records)
        elapsed = perf_counter() - start
        return ExecutionBenchmarkResult("transaction_cost_aggregation", len(records), elapsed)

    def _benchmark_stress_test(
        self,
        records: tuple[ExecutionCalibrationRecord, ...],
    ) -> ExecutionBenchmarkResult:
        start = perf_counter()
        _ = ExecutionStressTestEngine().run(
            records=records,
            scenario=_stress_scenario(),
            baseline_borrow=20.0,
            baseline_margin_interest=20.0,
        )
        elapsed = perf_counter() - start
        return ExecutionBenchmarkResult("execution_stress_test", len(records), elapsed)


def _records(n: int) -> tuple[ExecutionCalibrationRecord, ...]:
    ts = datetime(2027, 1, 15, 15, 0, tzinfo=UTC)
    rows: list[ExecutionCalibrationRecord] = []
    for idx in range(n):
        rows.append(
            ExecutionCalibrationRecord(
                symbol="SPY" if idx % 2 == 0 else "QQQ",
                contract_identifier=f"OPT-{idx}",
                timestamp=ts,
                side=ExecutionSide.BUY,
                action=ExecutionAction.OPEN,
                order_type=ExecutionOrderType.LIMIT,
                requested_quantity=10,
                filled_quantity=8,
                request_price=2.0,
                bid=1.95,
                ask=2.05,
                midpoint=2.0,
                last=2.0,
                fill_price=2.03,
                spread_width=0.1,
                quote_age_seconds=10.0,
                volume=500,
                open_interest=3000,
                implied_volatility=0.25,
                delta=0.3,
                dte=30,
                underlying_price=500.0,
                market_regime=MarketRegime.NORMAL,
                liquidity_regime=LiquidityRegime.NORMAL,
                volatility_regime=VolatilityRegime.MEDIUM,
                execution_delay_seconds=3.0,
                commission=1.3,
                exchange_fees=0.1,
                slippage=0.03,
                spread_capture=0.02,
                partial_fill=True,
                cancelled=False,
                source_type=ExecutionSourceType.SYNTHETIC_BACKTEST,
                provider_manifest="m1",
                broker_policy_version="generic:v1",
                metadata={"strategy_family": "iron_condors"},
            )
        )
    return tuple(rows)


def _stress_scenario():
    from .execution_calibration import ExecutionStressScenario

    return ExecutionStressScenario(name="benchmark_stress", spread_multiplier=2.0)
