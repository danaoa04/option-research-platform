# Success Metrics

## Overview

Success for the platform will be measured through engineering quality, research reliability, and platform usability.

## Metrics

- Reproducible backtests with complete metadata and deterministic outputs.
- 100% of provider entries are default-disabled in configuration and use environment-variable secret references.
- Dataset manifests serialize deterministically and preserve stable checksums for equivalent inputs.
- Incremental update planning requests only missing date ranges and avoids duplicate downloads.
- Cache integrity verification detects corruption and supports safe cleanup/invalidation without data races.
- Validation reports expose severity-level summaries and policy-driven fail-fast/collect-all behavior.
- Benchmark suite remains opt-in and does not impact default lint or test runtime.
- Database schema creation and migration tests run fully offline and deterministically in CI.
- Repository upsert and date-range query paths handle duplicates safely and preserve nullable vendor fields.
- Transaction rollback tests prove failed writes do not leave partial committed state.
- Batch ingestion services process deterministic chunks with explicit duplicate policy outcomes.
- As-of queries are verified to avoid look-ahead bias and to report stale-age when nearest-prior data is used.
- Corporate-action adjustment policies are deterministic and produce explicit warnings when action inputs are incomplete.
- Announcement-aware and effective-date knowledge policies are both tested to prevent forward-looking leakage.
- Immutable dataset snapshots can be verified and compared deterministically across runs.
- Audit events provide traceable lineage for snapshot creation and checksum-validation outcomes.
- Volatility term-structure outputs (classification, slope, curvature, forward-IV, and front/back metrics) are deterministic for identical snapshot/config inputs.
- Term-structure research features explicitly report that contango/backwardation are filters, not guaranteed profit signals.
- Multi-expiry spread research supports calendar, diagonal, double-calendar, and double-diagonal structures with call/put comparisons.
- Entry/exit filters are fully auditable and reproducible with no-look-ahead-safe as-of alignment.
- Historical and model-estimated probability outputs include calibration diagnostics and out-of-sample reporting.
- Walk-forward and regime analysis reports remain leakage-free and reproducible under fixed seeds/configuration.
- Volatility-spread simulations include realistic bid/ask, slippage, commission, and liquidity assumptions.
- Validation failures are surfaced before persistence for crossed markets, invalid strikes/timestamps, and manifest-contract mismatches.
- High coverage of validation scenarios for Greeks, pricing, assignment, margin, and execution.
- Clear and timely support for new data providers and strategies through the plugin architecture.
- Strong usability of the GUI for strategy construction, execution modeling, and result exploration.
- Adoption of documentation, standards, and workflows by contributors and research users.
- Frontend feature modules can be added without coupling to backend database model types.
- New pages and charts can be registered via plugin registry without editing core navigation logic.
- Typed frontend API contracts remain versionable and validated before UI rendering.
- Browser and Tauri desktop builds share a single frontend codebase without Electron dependencies.
- Workspace usability targets are met for saved layouts, keyboard shortcuts, guided setup, accessibility, and reversible strategy configuration.
- Greeks outputs (first-order and higher-order) are deterministic for identical inputs across single, batch, and portfolio calculations.
- Finite-difference verification keeps primary and selected higher-order Greeks within declared relative-error stability tolerances.
- Portfolio aggregation preserves expected sign behavior for long/short quantity and contract multiplier scaling.
- Structured warnings reliably flag degenerate inputs, near-expiry numerical instability, and unsupported verification dimensions.
- Pricing model routing is deterministic from stored contract metadata (exercise, settlement, underlying, dividends) with selected model and reason in outputs.
- American equity/ETF option pricing via CRR passes convergence and early-exercise behavior checks under deterministic settings.
- Black-76 futures-option pricing and first-order Greeks remain reproducible against published references.
- American-style Greeks expose first-order numerical sensitivities and explicit unsupported higher-order capabilities.
- Historical execution workflows preserve bid/ask as source-of-truth and never overwrite quote history with theoretical values.
- Implied-volatility inversion routes by contract metadata and selected pricing model with deterministic outcomes.
- Solver fallback sequence and convergence diagnostics are reproducible under fixed config.
- Invalid observed prices and unsupported contracts produce explicit structured failure states.
- Batch solving preserves input ordering and isolates per-contract failures without aborting full chains.
- Solver method fallback behavior is deterministic and auditable via method-attempt diagnostics metadata.
- American inversion outputs include tree-resolution sensitivity and model-setting metadata for model-risk monitoring.
- Quote-policy behavior for crossed, stale, zero-bid, missing-ask, wide-spread, and out-of-bounds quotes is explicit and test-covered.
- No silent fallback from American inversion paths to Black-Scholes is allowed.
- Volatility-surface readiness metadata supports deferred smile/term/surface quality labeling without enabling live-surface construction yet.
- Historical-volatility estimators produce deterministic annualized outputs for identical OHLC inputs and config.
- Observation quality scoring produces stable component-level reason codes and reproducible exclusion recommendations.
- Surface node counts (`raw`, `cleaned`, `interpolated`) are deterministic for identical observations and build config.
- Forward-volatility diagnostics explicitly flag negative-forward-variance cases and never silently clamp to valid outputs.
- Regime labels and confidence outputs are deterministic for identical term-structure and realized-volatility inputs.
- Volatility time slices cannot be mutated after finalization and attempted mutations raise explicit errors.
- Nearest-prior finalized-surface queries remain no-look-ahead safe under all as-of test cases.
- Multi-expiry strategy definitions are deterministic and expose complete leg/expiry/strike/type/quantity/date metadata.
- Strategy state analytics deterministically track IV/RV, IV percentile/rank, selected Greeks, PnL, and intrinsic/extrinsic decomposition.
- Regime classification consistently labels curve shape, earnings distortion, IV expansion/contraction, and realized-volatility states.
- Opportunity scoring remains explainable with reproducible component-level contributions, diagnostics, and warnings.
- Exhaustive parameter sweeps are deterministic, stable-ordered, and reproducible with fixed grids.
- Research run persistence captures configuration, parameters, software version, manifest lineage, checksums, timestamps, quality scores, and summary metrics.
- Research opportunity queries are no-look-ahead safe for all as-of ranking endpoints.
- Historical and model-estimated probabilities are always emitted with distinct labels and never mislabeled.
- Model probability simulation is deterministic for fixed seeds/configuration and includes reproducibility metadata.
- Per-leg model routing is auditable and respects configured American models for American-style contracts.
- No silent portfolio-wide fallback to Black-Scholes occurs when mixed contract styles are present.
- Lifecycle policy evaluation emits deterministic trigger reason codes and diagnostics.
- Calibration reports include reliability buckets, Brier score, and calibration-error summaries with sparse-bucket warnings.
- Regime-conditioned ranking remains explainable through component contributions and effective weights.
- Deterministic refinement outputs include constrained candidates, Pareto-front membership, and stable tie-breaking.
- Probability-run persistence rejects missing reproducibility configuration/metadata fields before write.
- Optimization problem definitions are fully reproducible with persisted parameter spaces, objectives, constraints, candidate ordering, and checksums.
- Candidate generation remains deterministic across exhaustive, coarse-to-fine, and low-discrepancy placeholder modes for fixed inputs.
- Hard and soft constraints emit explicit structured outcomes with no silent candidate drops.
- Failed candidate evaluations are isolated and persisted without aborting entire optimization runs.
- Weighted, lexicographic, and Pareto rankings are deterministic with stable tie-breaking.
- Walk-forward split generation enforces no-look-ahead chronology and deterministic purge/embargo handling.
- Serial and thread-pool evaluation modes return consistent winner sets and preserved ordering under deterministic evaluators.
- Optimization benchmarks remain opt-in and excluded from normal test execution.
- Portfolio eligibility filtering emits explicit deterministic rejection reasons.
- Portfolio construction rejects future-dated candidate timestamps when an as-of timestamp is provided.
- Portfolio run persistence requires reproducibility metadata and writes normalized run artifacts deterministically.
- Portfolio checksum reconciliation is order-stable for allocation rows.
- Portfolio benchmark suite remains opt-in and excluded from default test execution.

## Sprint 6A Backtesting Event Loop Foundation

- Added deterministic historical event-loop architecture with no-look-ahead controls.
- Added provider-neutral order-intent and baseline research fill-model contracts.
- Added immutable event/trade/valuation/cash ledgers with reproducibility checksums.
- Added as-of nearest-prior query semantics and historical run-comparison support.
- Added expiration and corporate-action baseline handling with settlement deferred.

## Sprint 6B Update
- Added deterministic strategy state-machine support for multi-leg historical orchestration.
- Added explicit transition guards/actions, partial-fill reconciliation, and roll-planning scaffolding.
- Added PMCC/synthetic covered call and calendar/diagonal readiness metadata without live execution.
- Preserved no-look-ahead and nearest-prior semantics across lifecycle and query services.
