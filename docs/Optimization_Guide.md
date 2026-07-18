# Optimization Guide

Optimization evaluates deterministic parameter grids over the backtesting
foundation.

## Covered concepts

- explicit parameter spaces;
- constraints;
- candidate ranking;
- walk-forward validation;
- CPCV;
- robustness review;
- promotion gates.

## How to read the results

- In-sample scores show how a candidate fit the training window.
- Validation and test scores matter more than the best in-sample score.
- Robustness and drift summaries help detect fragile candidates.
- Promotion status should be treated as a research triage signal, not a live
  deployment instruction.

## Important caution

Do not present optimization output as guaranteed future performance. The
current UI and docs intentionally frame optimization as deterministic historical
research.
