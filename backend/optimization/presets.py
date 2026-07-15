"""Reusable calibration-aware constraint presets."""

from __future__ import annotations

from dataclasses import dataclass

from .models import ConstraintDefinition, ConstraintSeverity


@dataclass(slots=True, frozen=True)
class CalibrationConstraintPreset:
    name: str
    constraints: tuple[ConstraintDefinition, ...]

    def compose(self, other: CalibrationConstraintPreset) -> CalibrationConstraintPreset:
        return CalibrationConstraintPreset(
            name=f"{self.name}+{other.name}",
            constraints=self.constraints + other.constraints,
        )


def minimum_sample_size(minimum: int) -> CalibrationConstraintPreset:
    return CalibrationConstraintPreset(
        name="minimum_sample_size",
        constraints=(
            ConstraintDefinition(
                name="minimum_sample_size",
                severity=ConstraintSeverity.HARD,
                metric_key="sample_size_metric",
                operator=">=",
                threshold=float(minimum),
            ),
        ),
    )


def maximum_confidence_interval_width(maximum: float) -> CalibrationConstraintPreset:
    return CalibrationConstraintPreset(
        name="maximum_confidence_interval_width",
        constraints=(
            ConstraintDefinition(
                name="maximum_confidence_interval_width",
                severity=ConstraintSeverity.SOFT,
                metric_key="confidence_interval_width",
                operator="<=",
                threshold=maximum,
                penalty=0.05,
            ),
        ),
    )


def minimum_lower_confidence_bound(minimum: float) -> CalibrationConstraintPreset:
    return CalibrationConstraintPreset(
        name="minimum_lower_confidence_bound",
        constraints=(
            ConstraintDefinition(
                name="minimum_lower_confidence_bound",
                severity=ConstraintSeverity.HARD,
                metric_key="lower_confidence_bound",
                operator=">=",
                threshold=minimum,
            ),
        ),
    )


def maximum_calibration_error(maximum: float) -> CalibrationConstraintPreset:
    return CalibrationConstraintPreset(
        name="maximum_calibration_error",
        constraints=(
            ConstraintDefinition(
                name="maximum_calibration_error",
                severity=ConstraintSeverity.SOFT,
                metric_key="calibration_error",
                operator="<=",
                threshold=maximum,
                penalty=0.05,
            ),
        ),
    )


def maximum_brier_score(maximum: float) -> CalibrationConstraintPreset:
    return CalibrationConstraintPreset(
        name="maximum_brier_score",
        constraints=(
            ConstraintDefinition(
                name="maximum_brier_score",
                severity=ConstraintSeverity.SOFT,
                metric_key="brier_score",
                operator="<=",
                threshold=maximum,
                penalty=0.05,
            ),
        ),
    )


def overconfidence_penalty(threshold: float) -> CalibrationConstraintPreset:
    return CalibrationConstraintPreset(
        name="overconfidence_penalty",
        constraints=(
            ConstraintDefinition(
                name="overconfidence_penalty",
                severity=ConstraintSeverity.SOFT,
                metric_key="overconfidence_penalty",
                operator="<=",
                threshold=threshold,
                penalty=0.1,
            ),
        ),
    )


def underconfidence_penalty(threshold: float) -> CalibrationConstraintPreset:
    return CalibrationConstraintPreset(
        name="underconfidence_penalty",
        constraints=(
            ConstraintDefinition(
                name="underconfidence_penalty",
                severity=ConstraintSeverity.SOFT,
                metric_key="underconfidence_penalty",
                operator="<=",
                threshold=threshold,
                penalty=0.1,
            ),
        ),
    )


def sparse_regime_penalty(threshold: float) -> CalibrationConstraintPreset:
    return CalibrationConstraintPreset(
        name="sparse_regime_penalty",
        constraints=(
            ConstraintDefinition(
                name="sparse_regime_penalty",
                severity=ConstraintSeverity.SOFT,
                metric_key="sparse_regime_penalty",
                operator="<=",
                threshold=threshold,
                penalty=0.1,
            ),
        ),
    )


def low_quality_data_penalty(threshold: float) -> CalibrationConstraintPreset:
    return CalibrationConstraintPreset(
        name="low_quality_data_penalty",
        constraints=(
            ConstraintDefinition(
                name="low_quality_data_penalty",
                severity=ConstraintSeverity.SOFT,
                metric_key="quality_score",
                operator=">=",
                threshold=threshold,
                penalty=0.1,
            ),
        ),
    )


def minimum_regime_coverage(minimum: float) -> CalibrationConstraintPreset:
    return CalibrationConstraintPreset(
        name="minimum_regime_coverage",
        constraints=(
            ConstraintDefinition(
                name="minimum_regime_coverage",
                severity=ConstraintSeverity.HARD,
                metric_key="regime_coverage",
                operator=">=",
                threshold=minimum,
            ),
        ),
    )


def minimum_out_of_sample_fold_count(minimum: int) -> CalibrationConstraintPreset:
    return CalibrationConstraintPreset(
        name="minimum_out_of_sample_fold_count",
        constraints=(
            ConstraintDefinition(
                name="minimum_out_of_sample_fold_count",
                severity=ConstraintSeverity.HARD,
                metric_key="oos_fold_count",
                operator=">=",
                threshold=float(minimum),
            ),
        ),
    )
