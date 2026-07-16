"""Versioned ORATS mapping with raw vendor-value preservation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from backend.data.integration.models import QuarantineReason


class OratsSchemaError(ValueError):
    pass


@dataclass(slots=True, frozen=True)
class NormalizedOratsRecord:
    canonical: dict[str, Any]
    raw_vendor: dict[str, Any]
    source_row_id: str
    request_id: str
    provider_schema_version: str
    mapping_version: str
    provider_units: dict[str, str]
    provider_timestamp: str


_REQUIRED = ("ticker", "tradeDate", "expirDate", "strike", "callPut")
_MAP = {
    "ticker": "symbol",
    "expirDate": "expiration",
    "strike": "strike",
    "callPut": "option_type",
    "bid": "bid",
    "ask": "ask",
    "last": "last",
    "volume": "volume",
    "openInterest": "open_interest",
    "iv": "provider_implied_volatility",
    "delta": "provider_delta",
    "gamma": "provider_gamma",
    "theta": "provider_theta",
    "vega": "provider_vega",
    "rho": "provider_rho",
    "stockPrice": "underlying_price",
    "dte": "provider_dte",
    "optionSymbol": "provider_option_identifier",
    "multiplier": "multiplier",
    "exerciseStyle": "exercise_style",
    "settlementStyle": "settlement_style",
}
_NUMERIC = {
    "strike",
    "bid",
    "ask",
    "last",
    "provider_implied_volatility",
    "provider_delta",
    "provider_gamma",
    "provider_theta",
    "provider_vega",
    "provider_rho",
    "underlying_price",
    "provider_dte",
    "multiplier",
}


class OratsNormalizer:
    SUPPORTED_SCHEMAS = {"orats-eod-fixture-v1"}
    mapping_version = "orats-canonical-v1"

    def normalize(
        self,
        raw: Mapping[str, Any],
        *,
        request_id: str,
        row_number: int,
        schema_version: str,
    ) -> NormalizedOratsRecord:
        if schema_version not in self.SUPPORTED_SCHEMAS:
            raise OratsSchemaError(f"Unknown ORATS schema version: {schema_version}")
        missing = [field for field in _REQUIRED if raw.get(field) in (None, "")]
        if missing:
            raise OratsSchemaError(f"Missing required ORATS fields: {', '.join(missing)}")
        canonical: dict[str, Any] = {}
        try:
            for vendor, target in _MAP.items():
                if vendor in raw and raw[vendor] not in (None, ""):
                    value = raw[vendor]
                    canonical[target] = float(value) if target in _NUMERIC else value
            canonical["symbol"] = str(canonical["symbol"]).strip().upper()
            option_type = str(canonical["option_type"]).strip().upper()
            canonical["option_type"] = {"CALL": "C", "PUT": "P"}.get(option_type, option_type)
            expiration = date.fromisoformat(str(canonical["expiration"]))
            canonical["expiration"] = expiration.isoformat()
            timestamp = self._timestamp(raw)
            canonical["quote_timestamp"] = timestamp.astimezone(UTC).isoformat()
            canonical["provider"] = "orats"
            canonical["provider_schema_version"] = schema_version
            canonical["contract_identity"] = self.contract_identity(canonical)
        except (KeyError, TypeError, ValueError) as exc:
            raise OratsSchemaError("Unable to normalize ORATS record") from exc
        self._validate(canonical, raw)
        raw_vendor = dict(raw)
        row_payload = json.dumps(raw_vendor, sort_keys=True, default=str, separators=(",", ":"))
        row_hash = hashlib.sha256(row_payload.encode()).hexdigest()[:16]
        return NormalizedOratsRecord(
            canonical=canonical,
            raw_vendor=raw_vendor,
            source_row_id=f"{request_id}:{row_number}:{row_hash}",
            request_id=request_id,
            provider_schema_version=schema_version,
            mapping_version=self.mapping_version,
            provider_units={"iv": "decimal", "theta": "per_day", "vega": "per_vol_point"},
            provider_timestamp=str(raw.get("quoteTimestamp") or raw["tradeDate"]),
        )

    @staticmethod
    def _timestamp(raw: Mapping[str, Any]) -> datetime:
        timestamp = raw.get("quoteTimestamp")
        if timestamp:
            parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=ZoneInfo("America/New_York"))
            return parsed
        trade_date = date.fromisoformat(str(raw["tradeDate"]))
        return datetime.combine(trade_date, time(16), ZoneInfo("America/New_York"))

    @staticmethod
    def contract_identity(record: Mapping[str, Any]) -> str:
        option_id = record.get("provider_option_identifier")
        if option_id:
            return f"ORATS:{option_id}"
        multiplier = record.get("multiplier", 100)
        return ":".join(
            (
                str(record["symbol"]),
                str(record["expiration"]),
                f"{float(record['strike']):.6f}",
                str(record["option_type"]),
                f"{float(multiplier):.4f}",
            )
        )

    @staticmethod
    def _validate(record: Mapping[str, Any], raw: Mapping[str, Any]) -> None:
        if record["option_type"] not in {"C", "P"}:
            raise OratsSchemaError(QuarantineReason.MISSING_REQUIRED_IDENTIFIER.value)
        if float(record["strike"]) <= 0:
            raise OratsSchemaError(QuarantineReason.INVALID_STRIKE.value)
        bid, ask = record.get("bid"), record.get("ask")
        if bid is not None and float(bid) < 0 or ask is not None and float(ask) < 0:
            raise OratsSchemaError(QuarantineReason.IMPOSSIBLE_PRICE.value)
        if bid is not None and ask is not None and float(bid) > float(ask):
            raise OratsSchemaError(QuarantineReason.CROSSED_MARKET.value)
        iv = record.get("provider_implied_volatility")
        if iv is not None and not 0 < float(iv) <= 10:
            raise OratsSchemaError("invalid_provider_iv")
        dte = record.get("provider_dte")
        if dte is not None:
            expected = (
                date.fromisoformat(str(record["expiration"]))
                - date.fromisoformat(str(raw["tradeDate"]))
            ).days
            if abs(float(dte) - expected) > 1:
                raise OratsSchemaError("inconsistent_dte")
