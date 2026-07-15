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
