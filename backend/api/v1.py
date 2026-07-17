"""Versioned routes backed only by existing safe services."""

from __future__ import annotations

import os
from pathlib import Path

from backend.data.provider_api import ProviderApiService, quality_snapshot
from backend.release.migration import MigrationManager
from backend.release.provenance import collect_provenance
from fastapi import APIRouter

from .contracts import (
    API_VERSION,
    APPLICATION_VERSION,
    BUILD_IDENTIFIER,
    ApiEnvelope,
    EndpointCapability,
)

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
    database_path = os.environ.get("ORP_DATABASE_PATH")
    migration_status = (
        MigrationManager(Path(database_path)).status().value if database_path else "not_configured"
    )
    provenance = collect_provenance(
        os.environ.get("ORP_RELEASE_PROFILE", "development")
    ).serialize()
    return {
        "api_version": API_VERSION,
        "backend_build": BUILD_IDENTIFIER,
        "compatibility_status": "compatible",
        "build_provenance": provenance,
        "database_migration_status": migration_status,
        "endpoints": endpoints,
        "fixture_mode_supported": True,
        "migration_status": migration_status,
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
        "version": APPLICATION_VERSION,
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


@router.get("/providers/audit")
def provider_audit() -> dict[str, object]:
    return envelope(provider_service.provider_audit().data)


@router.get("/providers/{provider}/credential-status")
def provider_credential_status(provider: str) -> dict[str, object]:
    return envelope(provider_service.credential_status(provider).data)


@router.get("/providers/{provider}/validation-demo")
def provider_validation_demo(provider: str) -> dict[str, object]:
    return envelope(provider_service.validation_demo(provider).data)


@router.get("/providers/{provider}/readiness")
def provider_readiness(provider: str) -> dict[str, object]:
    return envelope(provider_service.readiness_report(provider).data)
