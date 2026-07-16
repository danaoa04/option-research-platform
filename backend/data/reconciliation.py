"""Deterministic cross-provider identity, divergence, precedence, and merge previews."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class DivergenceSeverity(StrEnum):
    INFORMATIONAL = "informational"
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"
    INCOMPARABLE = "incomparable"


class MergeAction(StrEnum):
    SELECT_PROVIDER = "select_provider"
    PRESERVE_MULTIPLE = "preserve_multiple"
    COMPOSITE = "composite"
    REJECT = "reject"
    QUARANTINE = "quarantine"
    MANUAL_REVIEW = "manual_review"


@dataclass(slots=True, frozen=True)
class ContractIdentity:
    underlying: str
    expiration: str
    strike: float
    option_type: str
    multiplier: float = 100.0
    exercise_style: str | None = None
    settlement_style: str | None = None
    occ_symbol: str | None = None
    adjusted_deliverable: str | None = None

    @property
    def checksum(self) -> str:
        payload = json.dumps(
            self.__dict__
            if hasattr(self, "__dict__")
            else {name: getattr(self, name) for name in self.__dataclass_fields__},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(slots=True, frozen=True)
class ProviderObservation:
    provider: str
    identity: ContractIdentity
    timestamp: str
    fields: Mapping[str, Any]
    source_checksum: str
    certification_score: float | None = None
    stale: bool = False


@dataclass(slots=True, frozen=True)
class Divergence:
    field: str
    providers: tuple[str, str]
    left: Any
    right: Any
    absolute_difference: float | None
    relative_difference: float | None
    severity: DivergenceSeverity
    reason: str


@dataclass(slots=True, frozen=True)
class ReconciliationPolicy:
    version: str = "1.0.0"
    provider_precedence: tuple[str, ...] = ("cboe", "orats", "databento", "polygon")
    absolute_tolerances: Mapping[str, float] = field(
        default_factory=lambda: {
            "bid": 0.05,
            "ask": 0.05,
            "underlying_price": 0.05,
            "multiplier": 0.0,
        }
    )
    relative_tolerances: Mapping[str, float] = field(
        default_factory=lambda: {"bid": 0.02, "ask": 0.02, "underlying_price": 0.001}
    )
    critical_fields: tuple[str, ...] = (
        "multiplier",
        "exercise_style",
        "settlement_style",
        "adjusted_deliverable",
    )


@dataclass(slots=True, frozen=True)
class MergePreview:
    action: MergeAction
    canonical_fields: Mapping[str, Any]
    field_provenance: Mapping[str, str]
    divergences: tuple[Divergence, ...]
    policy_version: str
    observations: tuple[ProviderObservation, ...]
    explanation: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class ConsensusResult:
    agreeing_providers: tuple[str, ...]
    dissenting_providers: tuple[str, ...]
    consensus_fields: Mapping[str, Any]
    unresolved_fields: tuple[str, ...]
    field_provenance: Mapping[str, tuple[str, ...]]
    policy_version: str
    confidence: float
    severity: DivergenceSeverity
    warnings: tuple[str, ...]
    checksum: str


def consensus(
    observations: tuple[ProviderObservation, ...],
    policy: ReconciliationPolicy = ReconciliationPolicy(),
) -> ConsensusResult:
    if len(observations) < 3:
        raise ValueError("Consensus requires at least three providers")
    if len({item.identity.checksum for item in observations}) != 1:
        raise ValueError("Consensus identity conflict requires manual review")
    fields: dict[str, Any] = {}
    provenance: dict[str, tuple[str, ...]] = {}
    unresolved = []
    agreeing: set[str] = set()
    dissenting: set[str] = set()
    for name in sorted({key for item in observations for key in item.fields}):
        groups: dict[str, list[ProviderObservation]] = {}
        for item in observations:
            if item.fields.get(name) is not None:
                key = json.dumps(item.fields[name], sort_keys=True, default=str)
                groups.setdefault(key, []).append(item)
        winner = (
            max(
                groups.values(),
                key=lambda group: (
                    len(group),
                    -min(_rank(item.provider, policy) for item in group),
                ),
            )
            if groups
            else []
        )
        if len(winner) > len(observations) / 2:
            fields[name] = winner[0].fields[name]
            provenance[name] = tuple(sorted(item.provider for item in winner))
            agreeing.update(provenance[name])
            dissenting.update(item.provider for item in observations if item not in winner)
        else:
            unresolved.append(name)
    critical = bool(set(unresolved) & set(policy.critical_fields))
    confidence = len(agreeing) / len(observations)
    severity = (
        DivergenceSeverity.CRITICAL
        if critical
        else (DivergenceSeverity.MODERATE if unresolved else DivergenceSeverity.INFORMATIONAL)
    )
    payload = json.dumps(
        {"fields": fields, "unresolved": unresolved, "policy": policy.version},
        sort_keys=True,
        default=str,
    ).encode()
    warnings = ("Critical metadata conflict was not auto-resolved",) if critical else ()
    return ConsensusResult(
        tuple(sorted(agreeing)),
        tuple(sorted(dissenting)),
        fields,
        tuple(unresolved),
        provenance,
        policy.version,
        confidence,
        severity,
        warnings,
        hashlib.sha256(payload).hexdigest(),
    )


def reconcile(
    observations: tuple[ProviderObservation, ...],
    policy: ReconciliationPolicy = ReconciliationPolicy(),
) -> MergePreview:
    if not observations:
        return MergePreview(
            MergeAction.REJECT, {}, {}, (), policy.version, (), ("No observations",)
        )
    identities = {item.identity.checksum for item in observations}
    if len(identities) != 1:
        return MergePreview(
            MergeAction.MANUAL_REVIEW,
            {},
            {},
            (),
            policy.version,
            observations,
            ("Contract identity conflict",),
        )
    ordered = sorted(
        observations,
        key=lambda item: (
            _rank(item.provider, policy),
            item.stale,
            item.provider,
            item.source_checksum,
        ),
    )
    divergences = _divergences(ordered, policy)
    if any(item.severity is DivergenceSeverity.CRITICAL for item in divergences):
        return MergePreview(
            MergeAction.QUARANTINE,
            {},
            {},
            divergences,
            policy.version,
            observations,
            ("Critical contract-definition conflict",),
        )
    fields: dict[str, Any] = {}
    provenance: dict[str, str] = {}
    for observation in ordered:
        if observation.stale:
            continue
        for name, value in sorted(observation.fields.items()):
            if value is not None and name not in fields:
                fields[name] = value
                provenance[name] = observation.provider
    action = (
        MergeAction.COMPOSITE if len(set(provenance.values())) > 1 else MergeAction.SELECT_PROVIDER
    )
    return MergePreview(
        action,
        fields,
        provenance,
        divergences,
        policy.version,
        observations,
        ("Fields selected by versioned provider precedence and freshness",),
    )


def _rank(provider: str, policy: ReconciliationPolicy) -> int:
    try:
        return policy.provider_precedence.index(provider)
    except ValueError:
        return len(policy.provider_precedence)


def _divergences(
    observations: list[ProviderObservation], policy: ReconciliationPolicy
) -> tuple[Divergence, ...]:
    output = []
    for index, left in enumerate(observations):
        for right in observations[index + 1 :]:
            for name in sorted(set(left.fields) & set(right.fields)):
                first, second = left.fields[name], right.fields[name]
                if first is None or second is None or first == second:
                    continue
                absolute = relative = None
                if isinstance(first, (int, float)) and isinstance(second, (int, float)):
                    absolute = abs(float(first) - float(second))
                    relative = absolute / max(abs(float(first)), abs(float(second)), 1e-12)
                    tolerated = absolute <= policy.absolute_tolerances.get(
                        name, 0.0
                    ) or relative <= policy.relative_tolerances.get(name, 0.0)
                else:
                    tolerated = False
                severity = (
                    DivergenceSeverity.INFORMATIONAL if tolerated else DivergenceSeverity.MODERATE
                )
                if name in policy.critical_fields and not tolerated:
                    severity = DivergenceSeverity.CRITICAL
                output.append(
                    Divergence(
                        name,
                        (left.provider, right.provider),
                        first,
                        second,
                        absolute,
                        relative,
                        severity,
                        "within tolerance" if tolerated else "values conflict",
                    )
                )
    return tuple(output)
