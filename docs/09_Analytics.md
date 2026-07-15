# Analytics

## Purpose

This document defines analytics conventions for Sprint 4F probability, expected value, lifecycle, calibration, and ranking outputs.

## Probability Taxonomy

Historical and model-estimated probabilities are separate classes of analytics and must never be relabeled:

- historical_probability_of_profit
- historical_target_profit_probability
- historical_touch_target_probability
- historical_expiration_profit_probability
- historical_loss_threshold_breach_probability
- model_probability_of_profit
- model_target_profit_probability
- model_touch_target_probability
- model_expiration_profit_probability
- model_loss_threshold_breach_probability

## Expected Value Taxonomy

- historical_expected_value
- model_estimated_expected_value

Both outputs include deterministic risk summaries when samples are available.

## Calibration

Given predicted probability $p_i$ and observed outcome $y_i \in \{0,1\}$:

- Brier score:
  $$
  \text{Brier} = \frac{1}{n}\sum_i (p_i - y_i)^2
  $$
- Bucket calibration error:
  $$
  \text{Calibration Error} = \sum_b w_b \cdot |\hat p_b - \hat y_b|
  $$

Reports include reliability buckets and sparse-bucket warnings.

## Lifecycle Analytics

Lifecycle analysis evaluates state paths against policy triggers:

- profit_target
- loss_limit
- dte_exit
- delta_threshold
- volatility_change
- term_structure_normalized
- earnings_event_exit
- max_holding_period

Each trigger emits reason code, timestamp, and diagnostic fields.

## Regime-Conditioned Ranking

Ranking is explainable and deterministic:

- effective weights are explicit
- component contributions are explicit
- confidence is bounded to $[0,1]$

## Reproducibility Requirements

- Fixed random seed for model simulation.
- Dataset manifests and software commit metadata are persisted.
- Result checksums are captured at run persistence.
- Query retrieval remains no-look-ahead safe via as-of filtering.

## Sprint 5A Optimization Analytics

Optimization candidate analytics include:

- objective metrics
- constraint results
- lifecycle outcomes
- regime metadata
- calibration metadata
- data-quality metrics
- sample size
- runtime
- status and failure reason
- reproducibility metadata

Objective examples supported in Sprint 5A:

- maximize: historical/model PoP, expected value, median return, Sharpe, Sortino, profit factor, theta capture, liquidity, quality
- minimize: drawdown, expected shortfall, tail loss, gamma exposure, vega exposure, capital usage, turnover, Brier score, calibration error

Constraint examples supported in Sprint 5A:

- long DTE greater than short DTE
- minimum liquidity and quality
- minimum sample size
- maximum tail loss
- exercise compatibility policies
- allowed regime filters

## Pareto and Dominance Diagnostics

Multi-objective diagnostics include:

- deterministic Pareto-front extraction
- dominated-candidate tracking (`dominated_by`)
- deterministic tie-breaking by score and candidate ID
- crowding-distance hook placeholder for future algorithms
