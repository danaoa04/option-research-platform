"""Typed loading and validation for provider configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

KNOWN_PROVIDER_NAMES = ("orats", "databento", "polygon", "cboe", "yahoo", "csv")
SECRET_FIELD_NAMES = ("password", "token", "secret", "api_key", "auth")


class ProviderConfigError(ValueError):
    """Raised when provider configuration cannot be loaded or validated."""


class MissingCredentialError(ProviderConfigError):
    """Raised when a required credential environment variable is absent."""


@dataclass(slots=True, frozen=True)
class ProviderSecrets:
    """Environment-variable references used for provider authentication."""

    values: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ProviderSettings:
    """Settings for a single provider adapter."""

    name: str
    enabled: bool = False
    dataset: str = "default"
    timeout_seconds: float = 30.0
    max_retries: int = 3
    backoff_seconds: float = 0.5
    base_url: str = ""
    credentials: ProviderSecrets = field(default_factory=ProviderSecrets)


@dataclass(slots=True, frozen=True)
class ProvidersConfiguration:
    """Typed container for configured providers."""

    providers: dict[str, ProviderSettings]
    future_providers: dict[str, ProviderSettings]


@dataclass(slots=True, frozen=True)
class ResolvedCredentials:
    """Resolved credentials whose representation never exposes values."""

    provider: str
    values: dict[str, str]
    source: str = "environment"

    def redacted(self) -> dict[str, str]:
        return {key: "***" for key in sorted(self.values)}

    def __repr__(self) -> str:
        return f"ResolvedCredentials(provider={self.provider!r}, values={self.redacted()!r})"


def resolve_credentials(
    settings: ProviderSettings,
    *,
    environ: dict[str, str] | None = None,
    required: bool = True,
) -> ResolvedCredentials:
    """Resolve configured ``*_env`` references without retaining variable names as secrets."""
    source = os.environ if environ is None else environ
    resolved: dict[str, str] = {}
    missing: list[str] = []
    for key, variable in settings.credentials.values.items():
        logical_key = key.removesuffix("_env")
        value = source.get(variable)
        if value:
            resolved[logical_key] = value
        else:
            missing.append(variable)
    if required and missing:
        raise MissingCredentialError(
            f"Missing credentials for provider '{settings.name}': {', '.join(sorted(missing))}"
        )
    return ResolvedCredentials(provider=settings.name, values=resolved)


def load_providers_configuration(path: str | Path) -> ProvidersConfiguration:
    """Load and validate provider settings from a YAML file."""
    config_path = Path(path)
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ProviderConfigError(f"Unable to read provider config: {config_path}") from exc
    except yaml.YAMLError as exc:
        raise ProviderConfigError(f"Invalid YAML in provider config: {config_path}") from exc

    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ProviderConfigError("Provider config root must be a mapping")

    providers = _load_provider_map(payload.get("providers"), allow_unknown=False)
    future_providers = _load_provider_map(payload.get("future_providers"), allow_unknown=True)

    missing = [name for name in KNOWN_PROVIDER_NAMES if name not in providers]
    if missing:
        raise ProviderConfigError(
            f"Missing required providers in config: {', '.join(sorted(missing))}"
        )

    return ProvidersConfiguration(providers=providers, future_providers=future_providers)


def _load_provider_map(raw: Any, *, allow_unknown: bool) -> dict[str, ProviderSettings]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ProviderConfigError("Provider map must be a mapping")

    parsed: dict[str, ProviderSettings] = {}
    for provider_name, raw_settings in raw.items():
        if not isinstance(provider_name, str) or not provider_name:
            raise ProviderConfigError("Provider names must be non-empty strings")

        normalized_name = provider_name.lower().strip()
        if not allow_unknown and normalized_name not in KNOWN_PROVIDER_NAMES:
            raise ProviderConfigError(f"Unknown provider in config: {provider_name}")

        if not isinstance(raw_settings, dict):
            raise ProviderConfigError(f"Provider '{provider_name}' settings must be a mapping")

        parsed[normalized_name] = _parse_provider_settings(normalized_name, raw_settings)

    return parsed


def _parse_provider_settings(name: str, settings: dict[str, Any]) -> ProviderSettings:
    enabled = _require_bool(settings.get("enabled", False), f"{name}.enabled")
    dataset = _require_non_empty_string(settings.get("dataset", "default"), f"{name}.dataset")
    timeout_seconds = _require_non_negative_float(
        settings.get("timeout_seconds", 30.0), f"{name}.timeout_seconds"
    )
    max_retries = _require_non_negative_int(settings.get("max_retries", 3), f"{name}.max_retries")
    backoff_seconds = _require_non_negative_float(
        settings.get("backoff_seconds", 0.5), f"{name}.backoff_seconds"
    )
    base_url = _require_non_empty_string(settings.get("base_url", ""), f"{name}.base_url")
    credentials = _parse_credentials(settings.get("credentials", {}), provider_name=name)

    return ProviderSettings(
        name=name,
        enabled=enabled,
        dataset=dataset,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        backoff_seconds=backoff_seconds,
        base_url=base_url,
        credentials=ProviderSecrets(values=credentials),
    )


def _parse_credentials(raw_credentials: Any, *, provider_name: str) -> dict[str, str]:
    if raw_credentials is None:
        return {}
    if not isinstance(raw_credentials, dict):
        raise ProviderConfigError(f"{provider_name}.credentials must be a mapping")

    parsed: dict[str, str] = {}
    for key, value in raw_credentials.items():
        if not isinstance(key, str) or not key:
            raise ProviderConfigError(f"{provider_name}.credentials keys must be non-empty strings")
        if not isinstance(value, str) or not value:
            raise ProviderConfigError(
                f"{provider_name}.credentials.{key} must be a non-empty string"
            )

        lowered_key = key.lower()
        if any(secret_name in lowered_key for secret_name in SECRET_FIELD_NAMES):
            if not lowered_key.endswith("_env"):
                message = (
                    f"{provider_name}.credentials.{key} must reference an "
                    "environment variable and end with '_env'"
                )
                raise ProviderConfigError(message)
            if not value.isidentifier() or value.upper() != value:
                message = (
                    f"{provider_name}.credentials.{key} must be an uppercase "
                    "environment variable name"
                )
                raise ProviderConfigError(message)

        parsed[key] = value

    return parsed


def _require_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ProviderConfigError(f"{field_name} must be a boolean")


def _require_non_empty_string(value: Any, field_name: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise ProviderConfigError(f"{field_name} must be a non-empty string")


def _require_non_negative_float(value: Any, field_name: str) -> float:
    if isinstance(value, (int, float)) and float(value) >= 0:
        return float(value)
    raise ProviderConfigError(f"{field_name} must be a non-negative number")


def _require_non_negative_int(value: Any, field_name: str) -> int:
    if isinstance(value, int) and value >= 0:
        return value
    raise ProviderConfigError(f"{field_name} must be a non-negative integer")
