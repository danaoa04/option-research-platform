"""Custom exceptions for provider-related failures."""

from __future__ import annotations


class ProviderError(Exception):
    """Base class for provider framework errors."""


class ProviderAlreadyRegisteredError(ProviderError):
    """Raised when a provider name is registered more than once."""


class ProviderNotFoundError(ProviderError):
    """Raised when a provider cannot be resolved from the registry."""


class ProviderInitializationError(ProviderError):
    """Raised when a provider cannot be created or initialized."""
