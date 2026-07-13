"""Metadata structures describing provider capabilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ProviderMetadata:
    """Metadata for a provider adapter."""

    name: str
    vendor: str
    description: str
    capabilities: list[str] = field(default_factory=list)
    version: str = "1.0.0"
    config_schema: dict[str, Any] | None = None
