"""Injectable ORATS transport boundary; default tests use the fake implementation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from .models import OratsDataRequest


class OratsTransportError(RuntimeError):
    def __init__(
        self, message: str, *, status_code: int | None = None, retry_after: float | None = None
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after

    @property
    def retryable(self) -> bool:
        return self.status_code in {408, 425, 429, 500, 502, 503, 504}


@dataclass(slots=True, frozen=True)
class OratsResponse:
    records: tuple[Mapping[str, Any], ...]
    request_id: str
    page_number: int
    next_cursor: str | None = None
    has_more: bool = False
    content_type: str = "application/json"
    rate_limit_remaining: int | None = None
    raw_checksum: str = ""

    def __post_init__(self) -> None:
        if not self.raw_checksum:
            payload = json.dumps(self.records, sort_keys=True, separators=(",", ":"), default=str)
            object.__setattr__(self, "raw_checksum", hashlib.sha256(payload.encode()).hexdigest())


class OratsTransport(Protocol):
    def request(
        self,
        request: OratsDataRequest,
        *,
        page: int,
        cursor: str | None,
        cancelled: Callable[[], bool] | None = None,
    ) -> OratsResponse: ...


@dataclass(slots=True)
class FakeOratsTransport:
    """Deterministic response/error queue with no network or sleeping."""

    responses: list[OratsResponse | Exception]
    calls: list[tuple[int, str | None]] = field(default_factory=list)

    def request(
        self,
        request: OratsDataRequest,
        *,
        page: int,
        cursor: str | None,
        cancelled: Callable[[], bool] | None = None,
    ) -> OratsResponse:
        del request
        if cancelled and cancelled():
            raise OratsTransportError("Request cancelled")
        self.calls.append((page, cursor))
        if not self.responses:
            raise OratsTransportError("Missing fixture page")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response
