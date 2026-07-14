"""Interfaces for pricing model implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import ExerciseStyle, PricingModelName, PricingRequest, PricingResult


class PricingModel(ABC):
    """Contract for option-pricing models."""

    model_name: PricingModelName
    supported_styles: set[ExerciseStyle]

    @abstractmethod
    def price(self, request: PricingRequest) -> PricingResult:
        """Price an option request and return deterministic calculation outputs."""
