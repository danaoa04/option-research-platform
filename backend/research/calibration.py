"""Calibration diagnostics for probability and opportunity score outputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .exceptions import CalibrationError


@dataclass(slots=True, frozen=True)
class CalibrationBucket:
    bucket_index: int
    lower: float
    upper: float
    predicted_mean: float
    observed_frequency: float
    sample_size: int


@dataclass(slots=True, frozen=True)
class CalibrationDiagnostics:
    brier_score: float
    calibration_error: float
    reliability_table: tuple[CalibrationBucket, ...]
    overconfidence: float
    underconfidence: float
    warnings: tuple[str, ...]


@dataclass(slots=True)
class ScoreCalibrationEngine:
    min_bucket_samples: int = 10

    def evaluate(
        self,
        *,
        predicted_probabilities: list[float],
        observed_successes: list[bool],
        bucket_count: int = 10,
        regime_labels: list[str] | None = None,
        timestamps: list[datetime] | None = None,
    ) -> CalibrationDiagnostics:
        if len(predicted_probabilities) != len(observed_successes):
            raise CalibrationError("predictions and outcomes length mismatch")
        if not predicted_probabilities:
            raise CalibrationError("predictions cannot be empty")
        if bucket_count <= 0:
            raise CalibrationError("bucket_count must be positive")

        buckets: list[list[tuple[float, bool]]] = [[] for _ in range(bucket_count)]
        for p, outcome in zip(predicted_probabilities, observed_successes, strict=True):
            clipped = max(0.0, min(1.0, p))
            index = min(bucket_count - 1, int(clipped * bucket_count))
            buckets[index].append((clipped, outcome))

        reliability: list[CalibrationBucket] = []
        ece = 0.0
        total = len(predicted_probabilities)
        warnings: list[str] = []
        for index, bucket in enumerate(buckets):
            if not bucket:
                continue
            predicted_mean = sum(item[0] for item in bucket) / len(bucket)
            observed_frequency = sum(1.0 for item in bucket if item[1]) / len(bucket)
            lower = index / bucket_count
            upper = (index + 1) / bucket_count
            reliability.append(
                CalibrationBucket(
                    bucket_index=index,
                    lower=lower,
                    upper=upper,
                    predicted_mean=predicted_mean,
                    observed_frequency=observed_frequency,
                    sample_size=len(bucket),
                )
            )
            ece += (len(bucket) / total) * abs(observed_frequency - predicted_mean)
            if len(bucket) < self.min_bucket_samples:
                warnings.append(
                    f"bucket {index} has sparse sample size ({len(bucket)})"
                )

        brier = sum(
            (max(0.0, min(1.0, p)) - (1.0 if y else 0.0)) ** 2
            for p, y in zip(predicted_probabilities, observed_successes, strict=True)
        ) / len(predicted_probabilities)

        overconfidence = sum(
            max(0.0, bucket.predicted_mean - bucket.observed_frequency)
            for bucket in reliability
        )
        underconfidence = sum(
            max(0.0, bucket.observed_frequency - bucket.predicted_mean)
            for bucket in reliability
        )

        if regime_labels is not None and len(regime_labels) != len(predicted_probabilities):
            raise CalibrationError("regime_labels length mismatch")
        if timestamps is not None and len(timestamps) != len(predicted_probabilities):
            raise CalibrationError("timestamps length mismatch")

        return CalibrationDiagnostics(
            brier_score=brier,
            calibration_error=ece,
            reliability_table=tuple(reliability),
            overconfidence=overconfidence,
            underconfidence=underconfidence,
            warnings=tuple(warnings),
        )
