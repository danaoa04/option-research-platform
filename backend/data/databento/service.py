"""Deterministic Databento batching, retry, ordering, and failure isolation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .models import DatabentoRequest
from .normalization import DatabentoNormalizer, DatabentoSchemaError, NormalizedDatabentoRecord
from .transport import DatabentoResponse, DatabentoTransport, DatabentoTransportError


@dataclass(slots=True, frozen=True)
class DatabentoFailure:
    batch: int
    code: str
    message: str


@dataclass(slots=True)
class DatabentoResult:
    records: list[NormalizedDatabentoRecord]
    failures: list[DatabentoFailure]
    completed_batches: tuple[int, ...]
    continuation: str | None
    duplicate_count: int
    cancelled: bool = False


class DatabentoAdapter:
    def __init__(
        self,
        transport: DatabentoTransport,
        normalizer: DatabentoNormalizer,
        *,
        maximum_attempts: int = 3,
        backoff: Callable[[int, float | None], None] | None = None,
    ) -> None:
        self.transport = transport
        self.normalizer = normalizer
        self.maximum_attempts = maximum_attempts
        self.backoff = backoff or (lambda attempt, retry_after: None)

    def run(
        self,
        request: DatabentoRequest,
        *,
        cancelled: Callable[[], bool] | None = None,
    ) -> DatabentoResult:
        records: list[NormalizedDatabentoRecord] = []
        failures: list[DatabentoFailure] = []
        completed: list[int] = []
        seen_batches: set[str] = set()
        seen_records: set[tuple[object, ...]] = set()
        continuation = request.continuation
        batch = 1
        duplicates = 0
        last_sequence: dict[int, int] = {}
        while True:
            if cancelled and cancelled():
                return DatabentoResult(
                    records, failures, tuple(completed), continuation, duplicates, True
                )
            response = self._request(request, batch, continuation, cancelled, failures)
            if response is None:
                break
            if response.batch_number != batch:
                failures.append(DatabentoFailure(batch, "missing_batch", "Batch was out of order"))
                break
            batch_key = f"{batch}:{response.checksum}"
            if batch_key in seen_batches:
                failures.append(
                    DatabentoFailure(batch, "duplicate_batch", "Duplicate batch detected")
                )
                break
            seen_batches.add(batch_key)
            for raw in response.records:
                try:
                    normalized = self.normalizer.normalize(
                        raw,
                        dataset=request.dataset,
                        schema=request.schema,
                        checksum=response.checksum,
                    )
                    canonical = normalized.canonical
                    instrument = int(canonical["instrument_id"])
                    sequence = int(canonical["sequence"])
                    if sequence < last_sequence.get(instrument, sequence):
                        raise DatabentoSchemaError("sequence_regression")
                    last_sequence[instrument] = sequence
                    identity = (instrument, canonical["event_timestamp"], sequence, request.schema)
                    if identity in seen_records:
                        duplicates += 1
                        continue
                    seen_records.add(identity)
                    records.append(normalized)
                except DatabentoSchemaError as exc:
                    failures.append(DatabentoFailure(batch, str(exc), str(exc)))
            completed.append(batch)
            if not response.has_more:
                break
            if response.continuation == continuation:
                failures.append(
                    DatabentoFailure(batch, "stalled_continuation", "Continuation did not advance")
                )
                break
            continuation = response.continuation
            batch += 1
        records.sort(
            key=lambda item: (
                item.canonical["event_timestamp"],
                item.canonical["sequence"],
                item.canonical["instrument_id"],
            )
        )
        return DatabentoResult(records, failures, tuple(completed), continuation, duplicates)

    def _request(
        self,
        request: DatabentoRequest,
        batch: int,
        continuation: str | None,
        cancelled: Callable[[], bool] | None,
        failures: list[DatabentoFailure],
    ) -> DatabentoResponse | None:
        for attempt in range(1, self.maximum_attempts + 1):
            try:
                return self.transport.request(
                    request, batch=batch, continuation=continuation, cancelled=cancelled
                )
            except DatabentoTransportError as exc:
                if not exc.retryable or attempt == self.maximum_attempts:
                    failures.append(DatabentoFailure(batch, "transport_failure", str(exc)))
                    return None
                self.backoff(attempt, exc.retry_after)
        return None
