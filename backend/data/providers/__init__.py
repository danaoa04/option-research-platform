"""Provider framework package for historical-data integrations."""

from .base import AbstractDataProvider, ProviderContext
from .cboe import CboeProvider
from .config import (
    MissingCredentialError,
    ProviderConfigError,
    ProvidersConfiguration,
    ProviderSecrets,
    ProviderSettings,
    ResolvedCredentials,
    load_providers_configuration,
    resolve_credentials,
)
from .databento import DatabentoProvider
from .exceptions import (
    ProviderAlreadyRegisteredError,
    ProviderError,
    ProviderInitializationError,
    ProviderNotFoundError,
)
from .metadata import ProviderCapabilities, ProviderMetadata
from .orats import OratsProvider
from .polygon import PolygonProvider
from .registry import ProviderRegistry

__all__ = [
    "AbstractDataProvider",
    "CboeProvider",
    "DatabentoProvider",
    "OratsProvider",
    "PolygonProvider",
    "MissingCredentialError",
    "ProviderCapabilities",
    "ProviderConfigError",
    "ProviderSecrets",
    "ProviderSettings",
    "ResolvedCredentials",
    "ProvidersConfiguration",
    "ProviderAlreadyRegisteredError",
    "ProviderContext",
    "ProviderError",
    "ProviderInitializationError",
    "ProviderMetadata",
    "ProviderNotFoundError",
    "ProviderRegistry",
    "load_providers_configuration",
    "resolve_credentials",
]
