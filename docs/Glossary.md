# Glossary

This glossary defines common user-facing terms used across the platform.

- Assignment: The process by which an option seller is obligated to fulfil the
  contract.
- Backtest: A replay of a strategy over historical market data.
- Calibration: Comparing model assumptions with observed or benchmarked
  outcomes.
- CPCV: Combinatorial purged cross-validation, used to test strategy stability
  while reducing leakage.
- Delta: Sensitivity of option value to a small move in the underlying.
- DTE: Days to expiration.
- Early exercise: Exercising an option before expiration when the contract
  allows it.
- Forward volatility: Implied volatility inferred between two expirations.
- Gamma: Sensitivity of delta to a small move in the underlying.
- IV: Implied volatility.
- IV percentile: Where current IV sits relative to the observed historical
  window.
- IV rank: A normalized range position of current IV within the observed
  historical window.
- Lineage: Traceability from imported data through normalization, validation,
  and downstream artifacts.
- Multi-leg strategy: A strategy composed of multiple options and/or stock
  legs.
- Pin risk: Risk around expiration when the underlying sits near a strike and
  assignment/exercise outcomes become uncertain.
- Replay: Deterministic review of historical research events and branch
  decisions.
- Reproducibility: The ability to reproduce a research result from a known
  dataset, configuration, parameters, and seed.
- Robustness: Stability of a research result across alternative windows,
  scenarios, or validation paths.
- Scenario: A deterministic stress case for portfolio or strategy analysis.
- Skew: The way implied volatility changes across strikes or deltas.
- Term structure: The way implied volatility changes across expirations.
- Theta: Sensitivity of option value to time decay.
- Vega: Sensitivity of option value to implied-volatility changes.
- Walk-forward: Sequential train/validate/test evaluation over time-split data.
- Weighted vega: A volatility exposure measure that weights contracts by a
  chosen maturity or risk convention.
