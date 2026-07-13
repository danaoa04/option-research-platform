"""Placeholder data validation schemas."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DataValidationResult:
    """Represents the result of a validation check."""

    valid: bool
    errors: list[str]
