from backend.data.providers.cboe import CboeProvider
from backend.data.providers.polygon import PolygonProvider
from backend.data.reconciliation import (
    ContractIdentity,
    DivergenceSeverity,
    MergeAction,
    ProviderObservation,
    reconcile,
)


def _observation(provider: str, **fields: object) -> ProviderObservation:
    identity = ContractIdentity("SPY", "2026-01-16", 500, "C")
    return ProviderObservation(provider, identity, "2025-01-02T15:00:00Z", fields, provider)


def test_field_precedence_and_provenance_are_deterministic():
    preview = reconcile(
        (
            _observation("polygon", bid=4.01, volume=100),
            _observation("cboe", bid=4.0, settlement_style="physical"),
        )
    )
    assert preview.action is MergeAction.COMPOSITE
    assert preview.canonical_fields["bid"] == 4.0
    assert preview.field_provenance == {
        "bid": "cboe",
        "settlement_style": "cboe",
        "volume": "polygon",
    }
    assert preview.divergences[0].severity is DivergenceSeverity.INFORMATIONAL


def test_contract_identity_and_critical_metadata_conflicts_require_review():
    different = ProviderObservation(
        "polygon",
        ContractIdentity("SPY", "2026-01-16", 505, "C"),
        "2025-01-02T15:00:00Z",
        {"bid": 3},
        "polygon",
    )
    assert reconcile((_observation("cboe", bid=4), different)).action is MergeAction.MANUAL_REVIEW
    conflict = reconcile(
        (
            _observation("cboe", multiplier=100),
            _observation("orats", multiplier=150),
        )
    )
    assert conflict.action is MergeAction.QUARANTINE


def test_new_provider_capabilities_remain_conservative():
    cboe = CboeProvider().metadata.capability_contract
    polygon = PolygonProvider().metadata.capability_contract
    assert cboe and cboe.option_contracts and not cboe.option_quotes
    assert polygon and polygon.pagination and not polygon.option_quotes
