from __future__ import annotations

from datetime import date

import pytest

from backend.data.orats.comparison import compare_provider_platform
from backend.data.orats.models import OratsDataRequest, OratsDatasetKind
from backend.data.orats.normalization import OratsNormalizer, OratsSchemaError
from backend.data.orats.service import OratsAdapter
from backend.data.orats.synchronization import OratsPartition, plan_orats_sync
from backend.data.orats.transport import FakeOratsTransport, OratsResponse, OratsTransportError
from backend.data.providers.orats import OratsProvider
from backend.data.update.planner import DateRange


def _record(**updates: object) -> dict[str, object]:
    record: dict[str, object] = {
        "ticker": "SPY",
        "tradeDate": "2025-01-02",
        "expirDate": "2025-01-17",
        "strike": 500,
        "callPut": "call",
        "bid": 4.0,
        "ask": 4.2,
        "iv": 0.2,
        "delta": 0.5,
        "gamma": 0.02,
        "theta": -0.1,
        "vega": 0.15,
        "rho": 0.01,
        "stockPrice": 500.0,
        "dte": 15,
    }
    record.update(updates)
    return record


def _request() -> OratsDataRequest:
    return OratsDataRequest(
        OratsDatasetKind.OPTION_QUOTES,
        ("spy",),
        date(2025, 1, 2),
        date(2025, 1, 3),
    )


def test_paginated_fake_transport_preserves_vendor_values_and_deduplicates():
    responses = [
        OratsResponse((_record(),), "request-1", 1, "next", True),
        OratsResponse((_record(), _record(strike=505)), "request-2", 2),
    ]
    result = OratsAdapter(FakeOratsTransport(responses)).run(_request())
    assert not result.failures
    assert len(result.records) == 2
    assert result.records[0].raw_vendor["iv"] == 0.2
    assert result.records[0].canonical["provider_implied_volatility"] == 0.2
    assert result.completed_pages == (1, 2)


def test_retry_does_not_sleep_and_crossed_market_is_quarantined():
    calls = []
    transport = FakeOratsTransport(
        [
            OratsTransportError("limited", status_code=429, retry_after=2),
            OratsResponse((_record(bid=5, ask=4),), "request-1", 1),
        ]
    )
    result = OratsAdapter(
        transport, backoff=lambda attempt, delay: calls.append((attempt, delay))
    ).run(_request())
    assert calls == [(1, 2)]
    assert result.progress.retries == 1
    assert len(result.quarantine) == 1


def test_unknown_schema_and_request_validation():
    with pytest.raises(OratsSchemaError, match="Unknown"):
        OratsNormalizer().normalize(
            _record(), request_id="x", row_number=1, schema_version="future"
        )
    with pytest.raises(ValueError, match="symbol"):
        OratsDataRequest(
            OratsDatasetKind.OPTION_QUOTES,
            (),
            date(2025, 1, 1),
            date(2025, 1, 2),
        )


def test_provider_capabilities_sync_and_comparison():
    capabilities = OratsProvider().metadata.capability_contract
    assert capabilities and capabilities.option_quotes and not capabilities.corporate_actions
    partition = OratsPartition(
        "SPY",
        DateRange(date(2025, 1, 2), date(2025, 1, 3)),
        "checksum",
        "orats-eod-fixture-v1",
        "orats-canonical-v1",
    )
    assert plan_orats_sync(
        _request(),
        (partition,),
        schema_version="orats-eod-fixture-v1",
        normalization_version="orats-canonical-v1",
    ).no_op
    report = compare_provider_platform(
        [({"provider_delta": 0.5}, {"delta": 0.48})], tolerances={"delta": 0.01}
    )
    assert report.metrics[0].outlier_count == 1
