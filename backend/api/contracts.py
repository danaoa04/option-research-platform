"""Stable response contracts for the local desktop API."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any

from backend.release.config import load_release_config

_RELEASE = load_release_config()
APPLICATION_VERSION = _RELEASE.versions.application_version
API_VERSION = _RELEASE.versions.api_version
SCHEMA_VERSION = "1.0.0"
BUILD_IDENTIFIER = (
    f"orp-{APPLICATION_VERSION}-protocol-{_RELEASE.versions.sidecar_protocol_version}"
)


def deterministic_value(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return deterministic_value(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): deterministic_value(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple, set)):
        return [deterministic_value(item) for item in value]
    return value


@dataclass(slots=True, frozen=True)
class ApiEnvelope:
    data: Any
    request_id: str = "server-generated"
    api_version: str = API_VERSION
    schema_version: str = SCHEMA_VERSION

    def serialize(self) -> dict[str, Any]:
        return {
            "api_version": self.api_version,
            "data": deterministic_value(self.data),
            "request_id": self.request_id,
            "schema_version": self.schema_version,
        }


@dataclass(slots=True, frozen=True)
class EndpointCapability:
    domain: str
    operations: tuple[str, ...]
    fixture_only: bool
    mutation: bool
    authorization: str = "local-desktop-process"
