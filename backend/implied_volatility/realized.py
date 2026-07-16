"""Historical and realized volatility estimators."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .models import (
    AnnualizationConvention,
    HistoricalVolatilityConfig,
    HistoricalVolatilityResult,
    HistoricalVolEstimator,
    MissingSessionPolicy,
    OHLCBar,
)


@dataclass(slots=True)
class HistoricalVolatilityCalculator:
    """Deterministic realized-volatility calculator across standard estimators."""

    def calculate(
        self,
        bars: list[OHLCBar],
        config: HistoricalVolatilityConfig,
    ) -> HistoricalVolatilityResult:
        if config.lookback_window <= 1:
            return HistoricalVolatilityResult(
                estimator=config.estimator,
                annualized_volatility=None,
                observations_used=0,
                warnings=("lookback window must be greater than 1",),
            )

        ordered = sorted(bars, key=lambda row: row.timestamp)
        if len(ordered) < config.lookback_window:
            return HistoricalVolatilityResult(
                estimator=config.estimator,
                annualized_volatility=None,
                observations_used=len(ordered),
                warnings=("insufficient data for configured lookback window",),
            )

        sample = ordered[-config.lookback_window :]
        warnings: list[str] = []

        if any(not row.split_adjusted for row in sample):
            warnings.append("non split-adjusted bars detected")

        if config.missing_session_policy == MissingSessionPolicy.STRICT:
            for idx in range(1, len(sample)):
                gap_days = (sample[idx].timestamp.date() - sample[idx - 1].timestamp.date()).days
                if gap_days > 3:
                    return HistoricalVolatilityResult(
                        estimator=config.estimator,
                        annualized_volatility=None,
                        observations_used=idx,
                        warnings=("missing sessions exceed strict policy",),
                    )

        annual_factor = (
            252.0 if config.annualization == AnnualizationConvention.TRADING_DAYS_252 else 365.0
        )

        if config.estimator == HistoricalVolEstimator.CLOSE_TO_CLOSE:
            value = _close_to_close(sample)
        elif config.estimator == HistoricalVolEstimator.PARKINSON:
            value = _parkinson(sample)
        elif config.estimator == HistoricalVolEstimator.GARMAN_KLASS:
            value = _garman_klass(sample)
        elif config.estimator == HistoricalVolEstimator.ROGERS_SATCHELL:
            value = _rogers_satchell(sample)
        else:
            value = _yang_zhang(sample)

        if value is None:
            warnings.append("estimator produced no result")
            return HistoricalVolatilityResult(
                estimator=config.estimator,
                annualized_volatility=None,
                observations_used=len(sample),
                warnings=tuple(warnings),
            )

        if value < 0.0:
            warnings.append("negative variance estimate encountered")
            return HistoricalVolatilityResult(
                estimator=config.estimator,
                annualized_volatility=None,
                observations_used=len(sample),
                warnings=tuple(warnings),
            )

        return HistoricalVolatilityResult(
            estimator=config.estimator,
            annualized_volatility=math.sqrt(value * annual_factor),
            observations_used=len(sample),
            warnings=tuple(warnings),
        )


def _log_ratio(numerator: float, denominator: float) -> float | None:
    if numerator <= 0.0 or denominator <= 0.0:
        return None
    return math.log(numerator / denominator)


def _close_to_close(bars: list[OHLCBar]) -> float | None:
    returns: list[float] = []
    for idx in range(1, len(bars)):
        value = _log_ratio(bars[idx].close, bars[idx - 1].close)
        if value is None:
            return None
        returns.append(value)
    if len(returns) < 2:
        return None
    mean_ret = sum(returns) / len(returns)
    variance = sum((ret - mean_ret) ** 2 for ret in returns) / (len(returns) - 1)
    return variance


def _parkinson(bars: list[OHLCBar]) -> float | None:
    n = len(bars)
    if n == 0:
        return None
    values: list[float] = []
    for bar in bars:
        value = _log_ratio(bar.high, bar.low)
        if value is None:
            return None
        values.append(value * value)
    return sum(values) / (4.0 * n * math.log(2.0))


def _garman_klass(bars: list[OHLCBar]) -> float | None:
    n = len(bars)
    if n == 0:
        return None
    values: list[float] = []
    for bar in bars:
        log_hl = _log_ratio(bar.high, bar.low)
        log_co = _log_ratio(bar.close, bar.open)
        if log_hl is None or log_co is None:
            return None
        values.append(0.5 * (log_hl**2) - (2.0 * math.log(2.0) - 1.0) * (log_co**2))
    return sum(values) / n


def _rogers_satchell(bars: list[OHLCBar]) -> float | None:
    n = len(bars)
    if n == 0:
        return None
    values: list[float] = []
    for bar in bars:
        log_ho = _log_ratio(bar.high, bar.open)
        log_hc = _log_ratio(bar.high, bar.close)
        log_lo = _log_ratio(bar.low, bar.open)
        log_lc = _log_ratio(bar.low, bar.close)
        if None in {log_ho, log_hc, log_lo, log_lc}:
            return None
        assert log_ho is not None
        assert log_hc is not None
        assert log_lo is not None
        assert log_lc is not None
        values.append(log_ho * log_hc + log_lo * log_lc)
    return sum(values) / n


def _yang_zhang(bars: list[OHLCBar]) -> float | None:
    if len(bars) < 3:
        return None

    overnight_returns: list[float] = []
    open_close_returns: list[float] = []
    for idx in range(1, len(bars)):
        overnight = _log_ratio(bars[idx].open, bars[idx - 1].close)
        if overnight is None:
            return None
        overnight_returns.append(overnight)

    for bar in bars:
        oc = _log_ratio(bar.close, bar.open)
        if oc is None:
            return None
        open_close_returns.append(oc)

    rs = _rogers_satchell(bars)
    if rs is None:
        return None

    n = float(len(bars))
    if n <= 2.0:
        return None

    overnight_mean = sum(overnight_returns) / len(overnight_returns)
    overnight_var = sum((r - overnight_mean) ** 2 for r in overnight_returns) / max(
        len(overnight_returns) - 1,
        1,
    )

    open_close_mean = sum(open_close_returns) / len(open_close_returns)
    open_close_var = sum((r - open_close_mean) ** 2 for r in open_close_returns) / max(
        len(open_close_returns) - 1,
        1,
    )

    k = 0.34 / (1.34 + (n + 1.0) / (n - 1.0))
    return overnight_var + k * open_close_var + (1.0 - k) * rs
