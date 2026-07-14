"""Interfaces for pricing model implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import (
    ExerciseStyle,
    ModelCapabilities,
    PricingModelName,
    PricingRequest,
    PricingResult,
)


class PricingModel(ABC):
    """Contract for option-pricing models."""

    model_name: PricingModelName
    supported_styles: set[ExerciseStyle]
    capabilities: ModelCapabilities

    @abstractmethod
    def price(self, request: PricingRequest) -> PricingResult:
        """Price an option request and return deterministic calculation outputs."""

    def price_batch(self, requests: list[PricingRequest]) -> list[PricingResult]:
        """Price multiple requests.

        Default implementation is deterministic single-request dispatch.
        """
        return [self.price(request) for request in requests]
