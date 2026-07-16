"""Explicit-threshold dataset quality certification."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum

from .models import IngestionResult


class CertificationLevel(StrEnum):
    REJECTED = "rejected"
    QUARANTINED = "quarantined"
    USABLE_WITH_WARNINGS = "usable_with_warnings"
    RESEARCH_CERTIFIED = "research_certified"
    HIGH_QUALITY = "high_quality"


@dataclass(slots=True, frozen=True)
class CertificationThresholds:
    maximum_quarantine_rate: float = 0.01
    maximum_crossed_market_rate: float = 0.001
    high_quality_score: float = 0.98
    research_score: float = 0.90


@dataclass(slots=True, frozen=True)
class DatasetCertification:
    dataset_identifier: str
    provider: str
    version: str
    record_count: int
    quarantine_count: int
    duplicate_count: int
    crossed_market_count: int
    quality_score: float
    level: CertificationLevel
    warnings: tuple[str, ...]
    reproducibility_checksum: str


def certify(
    dataset_identifier: str,
    provider: str,
    version: str,
    result: IngestionResult,
    thresholds: CertificationThresholds = CertificationThresholds(),
) -> DatasetCertification:
    total = result.rows_processed
    quarantine_rate = len(result.quarantine) / total if total else 1.0
    crossed = sum(item.reason.value == "crossed_market" for item in result.quarantine)
    crossed_rate = crossed / total if total else 0.0
    score = max(
        0.0, 1.0 - quarantine_rate - crossed_rate - (result.duplicates / total if total else 0.0)
    )
    warnings = []
    if quarantine_rate > thresholds.maximum_quarantine_rate:
        warnings.append("Quarantine rate exceeds threshold")
    if crossed_rate > thresholds.maximum_crossed_market_rate:
        warnings.append("Crossed-market rate exceeds threshold")
    if total == 0:
        level = CertificationLevel.REJECTED
    elif warnings:
        level = CertificationLevel.QUARANTINED
    elif score >= thresholds.high_quality_score:
        level = CertificationLevel.HIGH_QUALITY
    elif score >= thresholds.research_score:
        level = CertificationLevel.RESEARCH_CERTIFIED
    else:
        level = CertificationLevel.USABLE_WITH_WARNINGS
    payload = {
        "dataset": dataset_identifier,
        "provider": provider,
        "version": version,
        "rows": total,
        "accepted": result.rows_accepted,
        "quarantined": len(result.quarantine),
        "duplicates": result.duplicates,
    }
    checksum = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return DatasetCertification(
        dataset_identifier,
        provider,
        version,
        result.rows_accepted,
        len(result.quarantine),
        result.duplicates,
        crossed,
        round(score, 6),
        level,
        tuple(warnings),
        checksum,
    )
