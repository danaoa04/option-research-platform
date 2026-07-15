# Strategy Analytics

## Scope

This document defines deterministic analytics produced by the Sprint 4E research engine.

## Return Statistics

Given a return series $r_1, \dots, r_n$:

- historical POP: $\frac{\#\{r_i > 0\}}{n}$
- expected value: $\mathbb{E}[r] = \frac{1}{n}\sum r_i$
- sample standard deviation:
  $$
  \sigma = \sqrt{\frac{1}{n-1}\sum_{i=1}^{n}(r_i-\bar r)^2}
  $$
- median return: middle ordered value (or midpoint of middle pair)

## Risk-Adjusted Metrics

- Sharpe:
  $$
  \text{Sharpe} = \frac{\mathbb{E}[r] - r_f}{\sigma}
  $$
- Sortino (downside deviation $\sigma_d$):
  $$
  \text{Sortino} = \frac{\mathbb{E}[r] - r_f}{\sigma_d}
  $$

Sprint 4E uses deterministic $r_f = 0$ by default.

## Drawdown

With cumulative PnL curve $P_t = \sum_{i=1}^{t} r_i$ and rolling peak $M_t = \max_{k \le t} P_k$:

$$
\text{drawdown}_t = P_t - M_t, \quad
\text{max drawdown} = \left|\min_t \text{drawdown}_t\right|
$$

## Streak Analytics

- win streak: longest consecutive run with $r_i > 0$
- loss streak: longest consecutive run with $r_i < 0$

## Greek Exposure Analytics

Using state series samples:

- theta capture: $\sum_t \Theta_t$
- vega exposure: mean absolute vega, $\frac{1}{n}\sum_t |\nu_t|$
- gamma exposure: mean absolute gamma, $\frac{1}{n}\sum_t |\Gamma_t|$

## Opportunity Explainability

Opportunity scoring reports per-component explainability:

- normalized score
- weight
- weighted contribution
- feature-level details

This enables deterministic audit trails for every ranked opportunity.

## Sprint 4F Probability Labels

Probability outputs are explicitly typed and never relabeled:

- `historical_probability_of_profit`
- `historical_target_profit_probability`
- `historical_touch_target_probability`
- `historical_expiration_profit_probability`
- `historical_loss_threshold_breach_probability`
- `model_probability_of_profit`
- `model_target_profit_probability`
- `model_touch_target_probability`
- `model_expiration_profit_probability`
- `model_loss_threshold_breach_probability`

Historical and model-estimated probabilities must be interpreted independently.

## Expected Value Separation

Expected value reporting is split into:

- `historical_expected_value`: empirical outcome estimate from historical samples
- `model_estimated_expected_value`: path-simulated estimate under model assumptions

Additional deterministic risk outputs include:

- downside deviation
- expected shortfall
- tail percentiles
- profit factor
- skew and kurtosis

## Calibration Metrics

Given predicted probabilities $p_i$ and outcomes $y_i \in \{0,1\}$:

- Brier score:
  $$
  	ext{Brier} = \frac{1}{n}\sum_{i=1}^{n}(p_i - y_i)^2
  $$
- Reliability error (bucketed absolute difference):
  $$
  	ext{Calibration Error} = \sum_b w_b\,|\hat p_b - \hat y_b|
  $$

where $w_b$ is bucket weight, $\hat p_b$ bucket mean prediction, and $\hat y_b$ bucket empirical success rate.

## Lifecycle Trigger Analytics

Lifecycle events are policy triggers over state paths:

- profit target hit
- loss limit hit
- DTE threshold exit
- delta threshold exit
- IV change threshold exit
- term-structure normalization exit
- earnings-event exit
- max holding period exit

Each trigger records timestamp, reason code, and supporting diagnostics.
