"""Versioned routes backed only by existing safe services."""

from __future__ import annotations

from backend.data.provider_api import ProviderApiService, quality_snapshot
from fastapi import APIRouter

from .contracts import API_VERSION, BUILD_IDENTIFIER, ApiEnvelope, EndpointCapability

router = APIRouter(prefix=f"/{API_VERSION}")
provider_service = ProviderApiService()

CAPABILITIES = (
    EndpointCapability("system", ("health", "compatibility", "features"), False, False),
    EndpointCapability("providers", ("catalogue", "capabilities", "jobs", "alerts"), False, True),
    EndpointCapability("strategies", ("catalogue", "validation", "previews"), True, True),
    EndpointCapability("backtests", ("queries", "execution"), True, True),
    EndpointCapability("optimization", ("validation", "execution"), True, True),
    EndpointCapability("portfolio", ("analytics", "risk"), True, True),
    EndpointCapability("replay", ("sessions", "branches", "comparison"), True, True),
    EndpointCapability("volatility", ("analytics", "surfaces", "quality"), True, True),
)


def envelope(data: object) -> dict[str, object]:
    return ApiEnvelope(data).serialize()


@router.get("/health")
def health() -> dict[str, object]:
    endpoints = sorted(route.path for route in router.routes)
    return {
        "api_version": API_VERSION,
        "backend_build": BUILD_IDENTIFIER,
        "compatibility_status": "compatible",
        "database_migration_status": "not_configured",
        "endpoints": endpoints,
        "fixture_mode_supported": True,
        "migration_status": "not_configured",
        "schema_version": "1.0.0",
        "service": "Option Research Platform backend",
        "sidecar_ready": True,
        "status": "ok",
        "supported_features": [item.domain for item in CAPABILITIES],
        "supported_mutations": [
            "provider job create",
            "provider job cancel",
            "provider job resume",
        ],
        "version": "0.1.0",
    }


@router.get("/compatibility")
def compatibility() -> dict[str, object]:
    return envelope(CAPABILITIES)


@router.get("/providers")
def providers() -> dict[str, object]:
    return envelope(provider_service.providers().data)


@router.get("/providers/{provider}/capabilities")
def provider_capabilities(provider: str) -> dict[str, object]:
    return envelope(provider_service.capabilities(provider).data)


@router.get("/providers/{provider}/catalogue")
def provider_catalogue(provider: str) -> dict[str, object]:
    return envelope(provider_service.catalogue(provider).data)


@router.get("/providers/jobs")
def provider_jobs() -> dict[str, object]:
    jobs = tuple(provider_service.operations.jobs.values())
    return envelope(jobs)


@router.get("/providers/alerts")
def provider_alerts() -> dict[str, object]:
    return envelope(provider_service.alert_history().data)


@router.get("/providers/quality")
def provider_quality() -> dict[str, object]:
    return envelope(quality_snapshot(provider_service).data)
