"""No-look-ahead protections and information-set audit helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .exceptions import NoLookAheadError
from .models import AsOfPolicy, InformationSetAudit


@dataclass(slots=True, frozen=True)
class NoLookAheadGuard:
    """Enforce historical visibility constraints for event-time lookups."""

    strict: bool = True

    def assert_visible(self, *, as_of: datetime, record_timestamp: datetime) -> None:
        as_of_ts = _ensure_aware(as_of)
        record_ts = _ensure_aware(record_timestamp)
        if record_ts > as_of_ts and self.strict:
            raise NoLookAheadError(
                "record timestamp exceeds available information set "
                f"(as_of={as_of_ts.isoformat()} record={record_ts.isoformat()})"
            )

    def audit_lookup(
        self,
        *,
        lookup_key: str,
        requested_timestamp: datetime,
        observed_timestamp: datetime | None,
        as_of_policy: AsOfPolicy,
        source_manifest: str | None,
        source_ref: str | None,
        reason_code: str,
        metadata: dict[str, Any] | None = None,
    ) -> InformationSetAudit:
        requested_ts = _ensure_aware(requested_timestamp)
        observed_ts = _ensure_aware(observed_timestamp) if observed_timestamp is not None else None
        if observed_ts is not None:
            self.assert_visible(as_of=requested_ts, record_timestamp=observed_ts)

        return InformationSetAudit(
            lookup_key=lookup_key,
            requested_timestamp=requested_ts,
            observed_timestamp=observed_ts,
            as_of_policy=as_of_policy,
            source_manifest=source_manifest,
            source_ref=source_ref,
            reason_code=reason_code,
            metadata=dict(metadata or {}),
        )


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
