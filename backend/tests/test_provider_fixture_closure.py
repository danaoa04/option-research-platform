from backend.data.cboe import CboeNormalizer, certify_cboe
from backend.data.fixture_transport import (
    FixtureResponse,
    FixtureTransport,
    FixtureTransportError,
    collect_batches,
)
from backend.data.polygon import PolygonNormalizer, certify_polygon
from backend.data.provider_monitoring import calculate_monitoring
from backend.data.reconciliation import (
    ContractIdentity,
    DivergenceSeverity,
    ProviderObservation,
    consensus,
    reconcile,
)


def test_fixture_batches_retry_cancellation_and_failures():
    calls = []
    transport = FixtureTransport(
        [
            FixtureTransportError("retry", retryable=True),
            FixtureResponse(1, ({"x": 1},), "next", True),
            FixtureResponse(2, ({"x": 2},)),
        ]
    )
    assert len(collect_batches(transport, backoff=calls.append)) == 2
    assert calls == [1]
    try:
        collect_batches(FixtureTransport([FixtureResponse(2, ())]))
    except FixtureTransportError as exc:
        assert str(exc) == "missing_batch"
    else:
        raise AssertionError("missing batch accepted")


def test_cboe_normalization_certification_and_rejection():
    raw = {
        "underlying": "SPX",
        "option_id": "SPX-1",
        "expiration": "2026-01-16",
        "strike": 5000,
        "option_type": "C",
        "multiplier": 100,
        "exercise_style": "european",
        "settlement_style": "cash",
        "bid": 10,
        "ask": 11,
    }
    record = CboeNormalizer().normalize(
        raw, schema="cboe-quote-v1", source_file="fixture.json", row=1, checksum="abc"
    )
    assert record.raw == raw
    assert certify_cboe([record]).level == "research_certified"
    try:
        CboeNormalizer().normalize(
            {**raw, "multiplier": None},
            schema="cboe-quote-v1",
            source_file="x",
            row=1,
            checksum="x",
        )
    except ValueError as exc:
        assert str(exc) == "missing_multiplier"
    else:
        raise AssertionError("missing multiplier inferred")


def test_polygon_normalization_certification_and_monitoring():
    raw = {
        "id": "q1",
        "underlying_ticker": "SPY",
        "sip_timestamp": 1,
        "bid_price": 4,
        "ask_price": 5,
    }
    record = PolygonNormalizer().normalize(
        raw, schema="polygon-quote-v1", endpoint="quotes", checksum="def"
    )
    assert "implied_volatility" not in record.canonical
    assert certify_polygon([record]).level == "research_certified"
    snapshot = calculate_monitoring("polygon", requests=10, failures=2, missing_batches=1)
    assert snapshot.failure_rate == 0.2
    assert "missing batches" in snapshot.alerts


def test_every_provider_pair_and_multi_provider_consensus():
    identity = ContractIdentity("SPY", "2026-01-16", 500, "C")

    def observation(provider: str, bid: float) -> ProviderObservation:
        return ProviderObservation(
            provider, identity, "2025-01-02T15:00:00Z", {"bid": bid}, provider
        )

    providers = ("orats", "databento", "cboe", "polygon")
    for index, left in enumerate(providers):
        for right in providers[index + 1 :]:
            assert reconcile((observation(left, 4), observation(right, 4.01))).observations
    result = consensus(
        (
            observation("orats", 4),
            observation("cboe", 4),
            observation("polygon", 5),
        )
    )
    assert result.consensus_fields["bid"] == 4
    assert result.agreeing_providers == ("cboe", "orats")
    assert result.severity is DivergenceSeverity.INFORMATIONAL
