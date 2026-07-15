"""Deterministic historical regime classifier for calendar research."""

from __future__ import annotations

from dataclasses import dataclass

from .models import HistoricalRegimeFlag, HistoricalRegimeRecord, RegimeClassificationInput


@dataclass(slots=True)
class HistoricalRegimeEngine:
    flat_threshold: float = 0.005
    high_realized_vol_threshold: float = 0.30
    low_realized_vol_threshold: float = 0.12
    event_elevation_threshold: float = 0.05

    def classify(self, data: RegimeClassificationInput) -> HistoricalRegimeRecord:
        flags: list[HistoricalRegimeFlag] = []

        if abs(data.slope) <= self.flat_threshold:
            flags.append(HistoricalRegimeFlag.FLAT_CURVE)
        elif data.slope > 0.0:
            flags.append(HistoricalRegimeFlag.CONTANGO)
        else:
            flags.append(HistoricalRegimeFlag.BACKWARDATION)

        if (
            data.earnings_front_elevation is not None
            and data.earnings_front_elevation > self.event_elevation_threshold
        ):
            flags.append(HistoricalRegimeFlag.EARNINGS_DISTORTION)

        if data.atm_iv is not None and data.prior_atm_iv is not None:
            if data.atm_iv > data.prior_atm_iv:
                flags.append(HistoricalRegimeFlag.IV_EXPANSION)
            elif data.atm_iv < data.prior_atm_iv:
                flags.append(HistoricalRegimeFlag.IV_CONTRACTION)

        if data.realized_volatility is not None:
            if data.realized_volatility >= self.high_realized_vol_threshold:
                flags.append(HistoricalRegimeFlag.HIGH_REALIZED_VOL)
            elif data.realized_volatility <= self.low_realized_vol_threshold:
                flags.append(HistoricalRegimeFlag.LOW_REALIZED_VOL)

        confidence = min(1.0, 0.55 + (0.08 * len(flags)))
        metadata = {
            "slope": data.slope,
            "realized_volatility": data.realized_volatility,
            "atm_iv": data.atm_iv,
            "prior_atm_iv": data.prior_atm_iv,
        }

        return HistoricalRegimeRecord(
            as_of=data.as_of,
            symbol=data.symbol,
            flags=tuple(dict.fromkeys(flags)),
            confidence=confidence,
            metadata=metadata,
        )
