from __future__ import annotations

from pathlib import Path

import pytest

from backend.data.providers.config import (
    KNOWN_PROVIDER_NAMES,
    ProviderConfigError,
    load_providers_configuration,
)


def test_provider_config_loads_defaults_with_all_disabled() -> None:
    config_path = Path(__file__).resolve().parents[2] / "config" / "providers.yaml"

    loaded = load_providers_configuration(config_path)

    assert set(KNOWN_PROVIDER_NAMES).issubset(set(loaded.providers))
    assert all(settings.enabled is False for settings in loaded.providers.values())


def test_provider_config_rejects_non_env_secret_reference(tmp_path: Path) -> None:
    config_file = tmp_path / "providers.yaml"
    config_file.write_text(
        """
providers:
  orats:
    enabled: false
    dataset: options_eod
    timeout_seconds: 30.0
    max_retries: 3
    backoff_seconds: 0.5
    base_url: https://example.com
    credentials:
      api_key: real-secret-value
  databento:
    enabled: false
    dataset: d
    timeout_seconds: 30
    max_retries: 1
    backoff_seconds: 0.5
    base_url: https://example.com
    credentials: {}
  polygon:
    enabled: false
    dataset: d
    timeout_seconds: 30
    max_retries: 1
    backoff_seconds: 0.5
    base_url: https://example.com
    credentials: {}
  cboe:
    enabled: false
    dataset: d
    timeout_seconds: 30
    max_retries: 1
    backoff_seconds: 0.5
    base_url: https://example.com
    credentials: {}
  yahoo:
    enabled: false
    dataset: d
    timeout_seconds: 30
    max_retries: 1
    backoff_seconds: 0.5
    base_url: https://example.com
    credentials: {}
  csv:
    enabled: false
    dataset: d
    timeout_seconds: 0
    max_retries: 0
    backoff_seconds: 0
    base_url: file://local
    credentials: {}
future_providers: {}
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ProviderConfigError):
        load_providers_configuration(config_file)
