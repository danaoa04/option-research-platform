"""Exceptions for probability, lifecycle, calibration, and refinement workflows."""

from __future__ import annotations


class ResearchValidationError(ValueError):
    """Raised when research inputs fail deterministic validation."""


class SparseSampleWarningError(RuntimeError):
    """Raised when strict sparse-sample handling rejects a computation."""


class ModelSimulationError(RuntimeError):
    """Raised when model-based simulation cannot produce valid outcomes."""


class LifecyclePolicyError(ValueError):
    """Raised when lifecycle policy hooks are invalid or inconsistent."""


class CalibrationError(ValueError):
    """Raised when calibration diagnostics inputs are invalid."""


class RefinementError(ValueError):
    """Raised when deterministic refinement inputs are invalid."""
