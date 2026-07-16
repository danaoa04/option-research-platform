"""Versioned mappings from vendor columns to canonical fields."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class SchemaProfile:
    name: str
    version: str
    required_columns: tuple[str, ...]
    optional_columns: tuple[str, ...] = ()
    aliases: dict[str, tuple[str, ...]] = field(default_factory=dict)
    units: dict[str, str] = field(default_factory=dict)
    scaling: dict[str, float] = field(default_factory=dict)
    timestamp_convention: str = "timezone-required"
    known_limitations: tuple[str, ...] = ()

    @property
    def identifier(self) -> str:
        return f"{self.name}@{self.version}"


_ALIASES = {
    "symbol": ("ticker", "underlying_symbol"),
    "expiration": ("expiry", "expiration_date"),
    "option_type": ("call_put", "put_call", "right"),
    "quote_timestamp": ("timestamp", "quote_time", "datetime"),
    "open_interest": ("openinterest", "oi"),
    "implied_volatility": ("iv", "impliedvolatility"),
    "underlying_price": ("spot", "underlying_last"),
}
_REQUIRED = ("symbol", "expiration", "strike", "option_type", "quote_timestamp")
_OPTIONAL = (
    "occ_symbol",
    "bid",
    "ask",
    "last",
    "volume",
    "open_interest",
    "implied_volatility",
    "delta",
    "gamma",
    "theta",
    "vega",
    "rho",
    "underlying_price",
    "multiplier",
    "exercise_style",
    "settlement_style",
    "exchange",
    "currency",
)


def _profile(name: str, limitations: tuple[str, ...] = ()) -> SchemaProfile:
    return SchemaProfile(
        name, "1.0.0", _REQUIRED, _OPTIONAL, dict(_ALIASES), known_limitations=limitations
    )


_PROFILES = {
    name: _profile(
        name,
        ("Placeholder: validate against licensed vendor samples",)
        if name in {"orats", "databento", "cboe", "polygon"}
        else (),
    )
    for name in (
        "generic_csv",
        "generic_parquet",
        "orats",
        "databento",
        "cboe",
        "polygon",
        "custom",
    )
}


def list_schema_profiles() -> tuple[SchemaProfile, ...]:
    return tuple(_PROFILES[name] for name in sorted(_PROFILES))


def get_schema_profile(name: str) -> SchemaProfile:
    try:
        return _PROFILES[name]
    except KeyError as exc:
        raise KeyError(f"Unknown schema profile: {name}") from exc


def resolve_mapping(
    columns: list[str], profile: SchemaProfile, explicit: dict[str, str] | None = None
) -> dict[str, str]:
    """Map source to canonical columns, rejecting ambiguous aliases."""
    normalized = {column.strip().lower(): column for column in columns}
    mapping = dict(explicit or {})
    used_sources = set(mapping)
    for canonical in (*profile.required_columns, *profile.optional_columns):
        if canonical in mapping.values():
            continue
        candidates = [
            name for name in (canonical, *profile.aliases.get(canonical, ())) if name in normalized
        ]
        if len(candidates) > 1:
            raise ValueError(
                f"Ambiguous columns for '{canonical}': {', '.join(sorted(candidates))}"
            )
        if candidates:
            source = normalized[candidates[0]]
            if source not in used_sources:
                mapping[source] = canonical
                used_sources.add(source)
    missing = [name for name in profile.required_columns if name not in mapping.values()]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    return mapping
