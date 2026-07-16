from datetime import UTC, datetime

import pytest

from backend.data.databento.models import DatabentoRequest, DatabentoRequestKind, DatabentoSchema
from backend.data.databento.normalization import (
    DatabentoNormalizer,
    SymbolResolution,
    SymbolResolver,
)
from backend.data.databento.service import DatabentoAdapter
from backend.data.databento.transport import DatabentoResponse, FakeDatabentoTransport
from backend.data.provider_operations import ProviderCheckpoint, ProviderOperationsService
from backend.data.providers.databento import DatabentoProvider

START = datetime(2025, 1, 2, tzinfo=UTC)
END = datetime(2025, 2, 1, tzinfo=UTC)


def _resolver() -> SymbolResolver:
    return SymbolResolver(
        (
            SymbolResolution(
                "SPY 250117C00500000", 7, "SPY", START, END, "2025-01-17", 500, "C", 100
            ),
        )
    )


def _request() -> DatabentoRequest:
    return DatabentoRequest(
        DatabentoRequestKind.HISTORICAL,
        "SYNTHETIC.OPRA",
        DatabentoSchema.MBP_1,
        ("SPY",),
        START,
        END,
    )


def test_continuation_normalization_order_and_raw_preservation():
    late = {
        "ts_event": "2025-01-02T15:00:01Z",
        "instrument_id": 7,
        "sequence": 2,
        "bid_px": 4,
        "ask_px": 5,
    }
    early = {
        "ts_event": "2025-01-02T15:00:00Z",
        "instrument_id": 7,
        "sequence": 1,
        "bid_px": 3,
        "ask_px": 4,
    }
    transport = FakeDatabentoTransport(
        [DatabentoResponse("a", 1, (early,), "next", True), DatabentoResponse("b", 2, (late,))]
    )
    result = DatabentoAdapter(transport, DatabentoNormalizer(_resolver())).run(_request())
    assert result.completed_batches == (1, 2)
    assert result.records[0].canonical["sequence"] == 1
    assert result.records[0].raw_provider["bid_px"] == 3


def test_ambiguous_symbology_and_crossed_quote_are_explicit_failures():
    ambiguous = SymbolResolution("x", 7, "SPY", START, END, ambiguous=True)
    response = DatabentoResponse(
        "a",
        1,
        ({"ts_event": "2025-01-02T15:00:00Z", "instrument_id": 7, "bid_px": 5, "ask_px": 4},),
    )
    result = DatabentoAdapter(
        FakeDatabentoTransport([response]), DatabentoNormalizer(SymbolResolver((ambiguous,)))
    ).run(_request())
    assert result.failures[0].code == "ambiguous_symbology"


def test_request_checksum_operations_and_provider_capabilities():
    assert _request().checksum == _request().checksum
    operations = ProviderOperationsService()
    job = operations.create_job(
        "databento", {"dataset": "SYNTHETIC.OPRA", "request": _request().checksum}
    )
    operations.checkpoint(
        ProviderCheckpoint("databento", job.job_id, "batch-1", 1, None, "abc", True)
    )
    with pytest.raises(ValueError, match="changed"):
        operations.checkpoint(
            ProviderCheckpoint("databento", job.job_id, "batch-1", 1, None, "def", True)
        )
    provider = DatabentoProvider()
    assert provider.capability_states["vendor_iv_greeks"] == "unsupported"
