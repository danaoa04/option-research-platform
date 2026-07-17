from __future__ import annotations

from backend.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_versioned_health_exposes_desktop_compatibility_metadata() -> None:
    response = client.get("/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["api_version"] == "v1"
    assert payload["schema_version"] == "1.0.0"
    assert payload["sidecar_ready"] is True
    assert payload["fixture_mode_supported"] is True
    assert payload["supported_mutations"] == [
        "provider job create",
        "provider job cancel",
        "provider job resume",
    ]
    assert payload["endpoints"] == sorted(payload["endpoints"])


def test_provider_routes_serialize_deterministically_without_secrets() -> None:
    response = client.get("/v1/providers")
    assert response.status_code == 200
    payload = response.json()
    assert payload["data"] == ["cboe", "databento", "orats", "polygon"]
    assert payload["api_version"] == "v1"
    assert payload["request_id"] == "server-generated"
    assert "secret" not in str(payload).lower()


def test_compatibility_catalogue_marks_fixture_only_boundaries() -> None:
    response = client.get("/v1/compatibility")
    assert response.status_code == 200
    capabilities = response.json()["data"]
    by_domain = {item["domain"]: item for item in capabilities}
    assert by_domain["system"]["fixture_only"] is False
    assert by_domain["volatility"]["fixture_only"] is True
    assert by_domain["providers"]["authorization"] == "local-desktop-process"
