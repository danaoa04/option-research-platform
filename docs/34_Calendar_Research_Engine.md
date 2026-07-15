# Calendar and Multi-Expiry Research Engine

## Purpose

Sprint 4E introduces a deterministic, provider-neutral research engine for multi-expiration option strategies.

This engine is analytics-only:

- no trade execution
- no broker connectivity
- no GUI coupling
- no live API requirements

## Strategy Coverage

Supported strategy templates in `backend/research/models.py`:

- calendar spreads
- diagonal spreads
- double calendars
- double diagonals
- ratio calendars
- PMCC
- synthetic covered calls
- multi-expiry custom structures

Each strategy definition includes:

- legs
- expirations
- strikes
- option types
- quantities
- entry date
- exit date
- metadata

## Strategy State Through Time

`StrategyStatePoint` tracks deterministic time-series state including:

- implied volatility and realized volatility
- IV percentile and IV rank
- theta, gamma, vega
- charm, vanna, vomma
- PnL
- intrinsic value and extrinsic value

## Regime Classification

`HistoricalRegimeEngine` classifies historical dates into:

- contango
- backwardation
- flat curve
- earnings distortion
- IV expansion
- IV contraction
- high realized volatility
- low realized volatility

Regime outputs include confidence and deterministic metadata.

## Opportunity Scoring

`CalendarOpportunityScorer` consumes:

- term structure slope
- forward volatility
- realized volatility
- IV percentile
- IV rank
- smile skew
- kurtosis
- liquidity
- spread width
- open interest
- volume
- quality score

Outputs:

- opportunity score
- confidence
- diagnostics
- warnings
- component-level explainability (weight, normalized score, contribution)

## Multi-DTE Research

Default DTE buckets include:

- 7, 14, 21, 30, 45, 60, 90, 180, 365, 540

Arbitrary DTE combinations are supported by deterministic parameter grids.

## Historical Analytics

`HistoricalAnalyticsEngine` reports:

- historical POP
- average winner and average loser
- expected value
- median return and standard deviation
- Sharpe and Sortino
- max drawdown
- win streak and loss streak
- theta capture
- vega exposure
- gamma exposure

## Parameter Sweep Framework

`ParameterSweepEngine` performs exhaustive deterministic sweeps using Cartesian products over user-specified parameter sets.

No optimization algorithms are included in Sprint 4E.

## Persistence and Querying

Research outputs persist in:

- `research_runs`
- `research_opportunities`

Stored run metadata includes configuration, parameters, software version, dataset manifest, checksums, timestamps, quality score, and summary metrics.

No-look-ahead query methods include:

- best calendar opportunities
- highest POP runs
- highest EV runs
- best theta capture runs
- highest quality runs
- best term-structure opportunities
- best historical regime opportunities

All as-of queries enforce `timestamp <= as_of` filtering.

## Benchmarks

`CalendarResearchBenchmarkRunner` provides opt-in runtime benchmarks for:

- parameter sweep generation
- opportunity scoring throughput

Benchmarks are disabled by default and gated in tests by `RUN_OPT_IN_BENCHMARKS=1`.

## Known Limits

- No optimization search heuristics yet (planned for Sprint 4F).
- No trade simulation and no broker integration.
- Query ranking currently prioritizes deterministic scalar metrics over multi-objective ranking.
