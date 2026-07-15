# Sprint 7 Checklist

## Sprint 7C - Execution Calibration, Broker Policy Adapters, and Transaction-Cost Validation

- [x] Added deterministic execution-calibration domain module in backend/backtesting/execution_calibration.py.
- [x] Added fill-quality metrics and grouped aggregation for symbol, regime, strategy family, portfolio, and time-of-day views.
- [x] Added slippage, spread-capture, and partial-fill calibration engines with low-confidence warning behavior.
- [x] Added deterministic transaction-cost aggregation with explicit line-item decomposition.
- [x] Added research-only broker policy adapters (generic baseline, IBKR-style, tastytrade-style, Schwab/thinkorswim-style, and user-defined).
- [x] Added broker policy comparison engine with ambiguity warning propagation.
- [x] Added execution quality scoring with configurable component weights and confidence accounting.
- [x] Added real-vs-simulated comparison contracts for fill/cost/timing/fee mismatch diagnostics.
- [x] Added train/validation split and calibration-drift validation helpers.
- [x] Added market-impact placeholder model and multi-leg execution realism analyzer.
- [x] Added stress-test scenario catalog and deterministic stress test engine.
- [x] Added deterministic execution calibration checksum utilities for reproducibility.
- [x] Extended replay inspection with execution_context payload for execution diagnostics.
- [x] Extended backtest configuration with additive execution policy and calibration fields.
- [x] Added execution-calibration persistence schema and migration 0013_execution_calibration_policy_validation.py.
- [x] Added ORM entities, DTOs, repositories, persistence service, and query service for Sprint 7C artifacts.
- [x] Added deterministic unit tests for calibration logic, persistence round-trip, migration upgrade/downgrade, and opt-in benchmarks.
- [x] Added opt-in execution benchmarks gated by RUN_EXECUTION_BENCHMARKS.
- [x] Passed quality gates: make lint and make test.

## Known Boundaries and Non-Goals (Sprint 7C)

- [x] No live broker APIs.
- [x] No live order-routing or venue-specific matching simulation.
- [x] No claim of official fee/margin parity with brokers.
- [x] No production market-impact model; placeholder only.
- [x] No production execution engine integration.

## Deferred to Sprint 8+

- [ ] Live broker adapter and credentialed API connectivity.
- [ ] Official broker reconciliation workflows against statement exports.
- [ ] Venue-aware order-book and routing simulation.
- [ ] Production market-impact model calibration and monitoring.
- [ ] Automated drift alerting and scheduled recalibration pipelines.
