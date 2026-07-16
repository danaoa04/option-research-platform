"""Injectable Databento continuation transport."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from .models import DatabentoRequest


class DatabentoTransportError(RuntimeError):
    def __init__(
        self, message: str, *, retryable: bool = False, retry_after: float | None = None
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.retry_after = retry_after


@dataclass(slots=True, frozen=True)
class DatabentoResponse:
    request_id: str
    batch_number: int
    records: tuple[Mapping[str, Any], ...]
    continuation: str | None = None
    has_more: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)
    checksum: str = ""

    def __post_init__(self) -> None:
        if not self.checksum:
            raw = json.dumps(self.records, sort_keys=True, default=str, separators=(",", ":"))
            object.__setattr__(self, "checksum", hashlib.sha256(raw.encode()).hexdigest())


class DatabentoTransport(Protocol):
    def request(
        self,
        request: DatabentoRequest,
        *,
        batch: int,
        continuation: str | None,
        cancelled: Callable[[], bool] | None = None,
    ) -> DatabentoResponse: ...


@dataclass(slots=True)
class FakeDatabentoTransport:
    responses: list[DatabentoResponse | Exception]
    calls: list[tuple[int, str | None]] = field(default_factory=list)

    def request(
        self,
        request: DatabentoRequest,
        *,
        batch: int,
        continuation: str | None,
        cancelled: Callable[[], bool] | None = None,
    ) -> DatabentoResponse:
        del request
        if cancelled and cancelled():
            raise DatabentoTransportError("cancelled")
        self.calls.append((batch, continuation))
        if not self.responses:
            raise DatabentoTransportError("missing fixture batch")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response
