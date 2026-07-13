from __future__ import annotations

import time
from pathlib import Path

import pytest

from backend.data.cache.manager import CacheManager
from backend.data.providers.base import AbstractDataProvider
from backend.data.providers.exceptions import (
    ProviderAlreadyRegisteredError,
    ProviderNotFoundError,
)
from backend.data.providers.metadata import ProviderMetadata
from backend.data.providers.orats import OratsProvider
from backend.data.providers.registry import ProviderRegistry
from backend.data.validation.engine import ValidationEngine


class DummyProvider(AbstractDataProvider):
    """Simple provider used to exercise the base interface."""

    def fetch(self, symbol: str) -> dict[str, object]:
        return {"provider": "dummy", "symbol": symbol}


def test_provider_registry_registers_and_discovers_providers() -> None:
    registry = ProviderRegistry()

    registry.register("orats", OratsProvider)
    registry.register("dummy", DummyProvider)

    assert registry.get_provider_class("orats") is OratsProvider
    assert registry.get_provider_class("dummy") is DummyProvider
    assert "orats" in registry.list_providers()
    assert "dummy" in registry.list_providers()

    with pytest.raises(ProviderAlreadyRegisteredError):
        registry.register("orats", DummyProvider)

    with pytest.raises(ProviderNotFoundError):
        registry.get_provider_class("missing")


def test_provider_interface_requires_metadata_and_fetch_contract() -> None:
    metadata = ProviderMetadata(name="dummy", vendor="test", description="Test provider")
    provider = DummyProvider(metadata=metadata)

    assert provider.metadata.name == "dummy"
    assert provider.fetch("SPY") == {"provider": "dummy", "symbol": "SPY"}

    placeholder = OratsProvider(
        metadata=ProviderMetadata(name="orats", vendor="orats", description="")
    )

    with pytest.raises(NotImplementedError):
        placeholder.fetch("SPY")


def test_cache_manager_persists_and_expires_entries(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    manager = CacheManager(base_dir=cache_dir, default_ttl_seconds=0.02)

    manager.set("sample", {"value": 1}, version="v1")
    assert manager.get("sample") == {"value": 1}
    assert manager.contains("sample")

    time.sleep(0.05)

    assert manager.get("sample") is None
    assert manager.get_metadata("sample") is None


def test_validation_engine_reports_structured_issues() -> None:
    engine = ValidationEngine()
    records = [
        {
            "id": "1",
            "timestamp": "2024-01-02T00:00:00Z",
            "option_chain": [{"strike": 0.0, "expiration": "2024-01-19"}],
            "implied_volatility": 0.3,
            "delta": 0.5,
            "gamma": 0.02,
            "theta": -0.1,
            "vega": 0.2,
            "rho": 0.05,
            "underlying_price": 100.0,
        },
        {
            "id": "1",
            "timestamp": "2024-01-02T00:00:00Z",
            "option_chain": [{"strike": 0.0, "expiration": "2024-01-19"}],
            "implied_volatility": 0.3,
            "delta": 0.5,
            "gamma": 0.02,
            "theta": -0.1,
            "vega": 0.2,
            "rho": 0.05,
            "underlying_price": 100.0,
        },
        {
            "id": "2",
            "timestamp": "not-a-time",
            "option_chain": [],
            "implied_volatility": 1.5,
            "delta": 0.5,
            "gamma": 0.02,
            "theta": -0.1,
            "vega": 0.2,
            "rho": 0.05,
            "underlying_price": 0.0,
        },
    ]

    report = engine.validate_records(records)

    assert report.valid is False
    codes = {issue.code for issue in report.issues}
    assert {
        "duplicate_record",
        "missing_option_chain",
        "invalid_strike",
        "malformed_timestamp",
        "missing_underlying_price",
    }.issubset(codes)
