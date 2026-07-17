"""Stable response contracts for the local desktop API."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any

API_VERSION = "v1"
SCHEMA_VERSION = "1.0.0"
BUILD_IDENTIFIER = "sprint-11f.2-local"


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
