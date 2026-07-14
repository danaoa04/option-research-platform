"""Interfaces for Greeks model implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.pricing.models import ExerciseStyle, PricingModelName

from .models import GreeksRequest, GreeksResult


class GreeksModel(ABC):
    """Contract for analytic Greeks model implementations."""

    model_name: PricingModelName
    supported_styles: set[ExerciseStyle]

    @abstractmethod
    def calculate(self, request: GreeksRequest) -> GreeksResult:
        """Calculate Greeks for a single request."""
