"""ORATS pagination, retry, normalization, quarantine, and progress orchestration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from backend.data.integration.models import QuarantineReason, QuarantineRecord, SourceMetadata

from .catalogue import get_dataset
from .models import OratsDataRequest, OratsProgress
from .normalization import NormalizedOratsRecord, OratsNormalizer, OratsSchemaError
from .transport import OratsResponse, OratsTransport, OratsTransportError


@dataclass(slots=True, frozen=True)
class OratsFailure:
    page: int
    cursor: str | None
    attempts: int
    message: str


@dataclass(slots=True)
class OratsRunResult:
    records: list[NormalizedOratsRecord]
    quarantine: list[QuarantineRecord]
    failures: list[OratsFailure]
    progress: OratsProgress
    completed_pages: tuple[int, ...]
    continuation_cursor: str | None
    cancelled: bool = False


class OratsAdapter:
    """Runs validated requests through an injected transport without owning credentials."""

    def __init__(
        self,
        transport: OratsTransport,
        *,
        normalizer: OratsNormalizer | None = None,
        max_attempts: int = 3,
        backoff: Callable[[int, float | None], None] | None = None,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self.transport = transport
        self.normalizer = normalizer or OratsNormalizer()
        self.max_attempts = max_attempts
        self.backoff = backoff or (lambda attempt, retry_after: None)

    def run(
        self,
        request: OratsDataRequest,
        *,
        cancelled: Callable[[], bool] | None = None,
        progress_callback: Callable[[OratsProgress], None] | None = None,
    ) -> OratsRunResult:
        dataset = get_dataset(request.dataset, request.frequency)
        progress = OratsProgress(symbols_planned=len(request.symbols))
        records: list[NormalizedOratsRecord] = []
        quarantine: list[QuarantineRecord] = []
        failures: list[OratsFailure] = []
        completed: list[int] = []
        page = 1
        cursor = request.resume_cursor
        seen_pages: set[str] = set()
        seen_rows: set[tuple[str, str]] = set()
        while True:
            if cancelled and cancelled():
                return OratsRunResult(
                    records, quarantine, failures, progress, tuple(completed), cursor, True
                )
            response, failure = self._request_page(request, page, cursor, cancelled, progress)
            if failure:
                failures.append(failure)
                progress.failures.append(failure.message)
                break
            assert response is not None
            page_key = f"{response.page_number}:{response.raw_checksum}"
            if page_key in seen_pages:
                failures.append(OratsFailure(page, cursor, 1, "Duplicate page detected"))
                break
            if response.page_number != page:
                failures.append(OratsFailure(page, cursor, 1, "Missing or out-of-order page"))
                break
            seen_pages.add(page_key)
            self._consume(response, dataset.schema_version, records, quarantine, seen_rows)
            completed.append(page)
            progress.pages_complete += 1
            progress.records_received += len(response.records)
            progress.records_accepted = len(records)
            progress.records_quarantined = len(quarantine)
            progress.rate_limit_remaining = response.rate_limit_remaining
            if progress_callback:
                progress_callback(progress)
            if not response.has_more:
                progress.symbols_complete = len(request.symbols)
                break
            if response.next_cursor == cursor and response.next_cursor is not None:
                failures.append(OratsFailure(page, cursor, 1, "Pagination cursor did not advance"))
                break
            cursor = response.next_cursor
            page += 1
        return OratsRunResult(records, quarantine, failures, progress, tuple(completed), cursor)

    def _request_page(
        self,
        request: OratsDataRequest,
        page: int,
        cursor: str | None,
        cancelled: Callable[[], bool] | None,
        progress: OratsProgress,
    ) -> tuple[OratsResponse | None, OratsFailure | None]:
        for attempt in range(1, self.max_attempts + 1):
            try:
                return self.transport.request(
                    request, page=page, cursor=cursor, cancelled=cancelled
                ), None
            except OratsTransportError as exc:
                if not exc.retryable or attempt == self.max_attempts:
                    return None, OratsFailure(page, cursor, attempt, str(exc))
                progress.retries += 1
                self.backoff(attempt, exc.retry_after)
        raise AssertionError("unreachable")

    def _consume(
        self,
        response: OratsResponse,
        schema_version: str,
        records: list[NormalizedOratsRecord],
        quarantine: list[QuarantineRecord],
        seen_rows: set[tuple[str, str]],
    ) -> None:
        normalizer = self.normalizer
        for row_number, raw in enumerate(response.records, start=1):
            source = SourceMetadata(
                response.request_id, response.raw_checksum, row_number, normalizer.mapping_version
            )
            try:
                normalized = normalizer.normalize(
                    raw,
                    request_id=response.request_id,
                    row_number=row_number,
                    schema_version=schema_version,
                )
                identity = (
                    normalized.canonical["contract_identity"],
                    normalized.canonical["quote_timestamp"],
                )
                if identity in seen_rows:
                    continue
                seen_rows.add(identity)
                records.append(normalized)
            except OratsSchemaError as exc:
                reason = next(
                    (item for item in QuarantineReason if item.value == str(exc)),
                    QuarantineReason.SCHEMA_MISMATCH,
                )
                quarantine.append(QuarantineRecord(reason, str(exc), dict(raw), source))
