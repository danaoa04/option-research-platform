"""Registry for discoverable data providers."""

from __future__ import annotations

from typing import Any, TypeVar

from .exceptions import ProviderAlreadyRegisteredError, ProviderNotFoundError
from .metadata import ProviderMetadata

ProviderClass = TypeVar("ProviderClass")


class ProviderRegistry:
    """Maintain a registry of provider classes and support lookup by name."""

    def __init__(self) -> None:
        self._providers: dict[str, type[Any]] = {}

    def register(self, name: str, provider_cls: type[Any]) -> None:
        """Register a provider class under a canonical name."""
        normalized_name = name.lower()
        if normalized_name in self._providers:
            raise ProviderAlreadyRegisteredError(f"Provider '{name}' is already registered")
        self._providers[normalized_name] = provider_cls

    def get_provider_class(self, name: str) -> type[Any]:
        """Return a provider class by its registered name."""
        normalized_name = name.lower()
        if normalized_name not in self._providers:
            raise ProviderNotFoundError(f"Provider '{name}' is not registered")
        return self._providers[normalized_name]

    def create_provider(self, name: str, metadata: ProviderMetadata) -> Any:
        """Instantiate a registered provider with the supplied metadata."""
        provider_cls = self.get_provider_class(name)
        return provider_cls(metadata=metadata)

    def list_providers(self) -> list[str]:
        """Return the sorted set of registered provider names."""
        return sorted(self._providers)
