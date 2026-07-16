"""Versioned backend-facing ORATS API presentation contracts."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from backend.data.integration.export import export_json

from .catalogue import ORATS_CATALOGUE
from .models import OratsDataRequest

API_VERSION = "1.0.0"


def credential_status(*, configured: bool, source: str = "environment") -> dict[str, Any]:
    return {
        "schema_version": API_VERSION,
        "provider": "orats",
        "configured": configured,
        "source": source,
    }


def catalogue_contract() -> dict[str, Any]:
    return {"schema_version": API_VERSION, "datasets": [asdict(item) for item in ORATS_CATALOGUE]}


def request_preview(request: OratsDataRequest) -> dict[str, Any]:
    return {
        "schema_version": API_VERSION,
        "provider": "orats",
        "request": asdict(request),
        "network_performed": False,
    }


def serialize_contract(value: Any, *, pretty: bool = False) -> str:
    return export_json(value, pretty=pretty, redact=True)
