"""Public provider facade for the offline-testable ORATS adapter."""

from __future__ import annotations

from datetime import date
from typing import Any

from backend.data.orats.models import OratsDataRequest, OratsDatasetKind
from backend.data.orats.service import OratsAdapter
from backend.data.orats.transport import OratsTransport

from .base import AbstractDataProvider, ProviderContext
from .metadata import ProviderCapabilities, ProviderMetadata


class OratsProvider(AbstractDataProvider):
    """ORATS provider facade; transport must be injected explicitly."""

    def __init__(
        self,
        metadata: ProviderMetadata | None = None,
        *,
        transport: OratsTransport | None = None,
    ) -> None:
        super().__init__(
            metadata
            or ProviderMetadata(
                name="orats",
                vendor="orats",
                description="Licensed ORATS historical data adapter",
                capability_contract=ProviderCapabilities(
                    option_contracts=True,
                    option_quotes=True,
                    bid_ask=True,
                    implied_volatility=True,
                    greeks=True,
                    underlying_prices=True,
                    dividends=False,
                    earnings=False,
                    corporate_actions=False,
                    settlement_metadata=False,
                    exercise_style=False,
                    adjusted_contracts=False,
                    end_of_day_frequency=True,
                    intraday_frequency=False,
                    bulk_download=True,
                    incremental_updates=True,
                    pagination=True,
                    compression=("gzip", "zip"),
                    checksums=True,
                    rate_limits=True,
                ),
            )
        )
        self.transport = transport

    def fetch(self, symbol: str, context: ProviderContext | None = None) -> dict[str, Any]:
        """Fetch a requested local/fake-transport date range and return typed run data."""
        if self.transport is None:
            raise RuntimeError(
                "ORATS transport is not configured; live access requires credentials"
            )
        metadata = context.metadata if context and context.metadata else {}
        start = date.fromisoformat(str(metadata.get("start_date", date.today().isoformat())))
        end = date.fromisoformat(str(metadata.get("end_date", start.isoformat())))
        request = OratsDataRequest(
            dataset=OratsDatasetKind.OPTION_QUOTES,
            symbols=(symbol,),
            start_date=start,
            end_date=end,
        )
        result = OratsAdapter(self.transport).run(request)
        return {
            "records": [record.canonical for record in result.records],
            "quarantine": result.quarantine,
            "failures": result.failures,
            "progress": result.progress,
        }
