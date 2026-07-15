"""Optimization subsystem exceptions."""

from __future__ import annotations


class OptimizationError(RuntimeError):
    """Base optimization subsystem error."""


class OptimizationValidationError(OptimizationError):
    """Raised when optimization problem definitions are invalid."""


class CandidateGenerationError(OptimizationError):
    """Raised when candidate generation cannot proceed."""


class CandidateEvaluationError(OptimizationError):
    """Raised when candidate evaluation fails unexpectedly."""


class ConstraintEvaluationError(OptimizationError):
    """Raised when constraints are malformed or cannot be evaluated."""


class WalkForwardSplitError(OptimizationError):
    """Raised when walk-forward split generation fails."""
