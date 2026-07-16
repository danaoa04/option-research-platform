"""Public provider facade for the offline-testable Databento adapter."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from backend.data.databento.models import (
    CapabilityState,
    DatabentoRequest,
    DatabentoRequestKind,
    DatabentoSchema,
)
from backend.data.databento.normalization import DatabentoNormalizer, SymbolResolver
from backend.data.databento.service import DatabentoAdapter
from backend.data.databento.transport import DatabentoTransport

from .base import AbstractDataProvider, ProviderContext
from .metadata import ProviderCapabilities, ProviderMetadata


class DatabentoProvider(AbstractDataProvider):
    """Databento facade with explicit injected transport and symbology."""

    def __init__(
        self,
        metadata: ProviderMetadata | None = None,
        *,
        transport: DatabentoTransport | None = None,
        resolver: SymbolResolver | None = None,
    ) -> None:
        super().__init__(
            metadata
            or ProviderMetadata(
                name="databento",
                vendor="databento",
                description="Dataset- and schema-dependent Databento historical adapter",
                capability_contract=ProviderCapabilities(
                    option_contracts=True,
                    option_quotes=True,
                    trades=True,
                    bid_ask=True,
                    bulk_download=True,
                    pagination=True,
                    compression=("zstd", "gzip"),
                    checksums=True,
                    incremental_updates=True,
                    rate_limits=True,
                ),
            )
        )
        self.transport = transport
        self.resolver = resolver
        self.capability_states = {
            "instrument_definitions": CapabilityState.SUPPORTED,
            "symbology": CapabilityState.SUPPORTED,
            "option_quotes": CapabilityState.DATASET_DEPENDENT,
            "option_trades": CapabilityState.DATASET_DEPENDENT,
            "vendor_iv_greeks": CapabilityState.UNSUPPORTED,
            "universal_us_options_coverage": CapabilityState.NOT_VALIDATED,
        }

    def fetch(self, symbol: str, context: ProviderContext | None = None) -> dict[str, Any]:
        """Run an offline/injected historical request for one symbol."""
        if self.transport is None or self.resolver is None:
            raise RuntimeError("Databento authenticated transport and symbology are not configured")
        details = context.metadata if context and context.metadata else {}
        start = datetime.fromisoformat(str(details.get("start", datetime.now(UTC).isoformat())))
        end = datetime.fromisoformat(
            str(details.get("end", (start + timedelta(days=1)).isoformat()))
        )
        request = DatabentoRequest(
            DatabentoRequestKind.HISTORICAL,
            str(details.get("dataset", "SYNTHETIC.OPRA")),
            DatabentoSchema(str(details.get("schema", DatabentoSchema.MBP_1.value))),
            (symbol,),
            start,
            end,
        )
        result = DatabentoAdapter(self.transport, DatabentoNormalizer(self.resolver)).run(request)
        return {
            "records": result.records,
            "failures": result.failures,
            "batches": result.completed_batches,
        }
