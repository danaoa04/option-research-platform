"""Shared deterministic offline batch transport for synthetic provider fixtures."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any


class FixtureTransportError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass(slots=True, frozen=True)
class FixtureResponse:
    batch: int
    records: tuple[Mapping[str, Any], ...]
    continuation: str | None = None
    has_more: bool = False
    source_file: str = "synthetic.json"
    checksum: str = ""

    def __post_init__(self) -> None:
        if not self.checksum:
            raw = json.dumps(self.records, sort_keys=True, separators=(",", ":"), default=str)
            object.__setattr__(self, "checksum", hashlib.sha256(raw.encode()).hexdigest())


@dataclass(slots=True)
class FixtureTransport:
    responses: list[FixtureResponse | Exception]
    calls: list[tuple[int, str | None]] = field(default_factory=list)

    def request(
        self,
        batch: int,
        continuation: str | None,
        cancelled: Callable[[], bool] | None = None,
    ) -> FixtureResponse:
        if cancelled and cancelled():
            raise FixtureTransportError("cancelled")
        self.calls.append((batch, continuation))
        if not self.responses:
            raise FixtureTransportError("missing_batch")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def collect_batches(
    transport: FixtureTransport,
    *,
    cancelled: Callable[[], bool] | None = None,
    attempts: int = 3,
    backoff: Callable[[int], None] | None = None,
) -> tuple[FixtureResponse, ...]:
    output: list[FixtureResponse] = []
    continuation = None
    seen: set[str] = set()
    batch = 1
    while True:
        for attempt in range(1, attempts + 1):
            try:
                response = transport.request(batch, continuation, cancelled)
                break
            except FixtureTransportError as exc:
                if not exc.retryable or attempt == attempts:
                    raise
                if backoff:
                    backoff(attempt)
        if response.batch != batch:
            raise FixtureTransportError("missing_batch")
        key = f"{batch}:{response.checksum}"
        if key in seen:
            raise FixtureTransportError("duplicate_batch")
        seen.add(key)
        output.append(response)
        if not response.has_more:
            return tuple(output)
        if response.continuation == continuation:
            raise FixtureTransportError("stalled_continuation")
        continuation = response.continuation
        batch += 1
