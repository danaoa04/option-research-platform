"""Conservative, fixture-validated ORATS dataset catalogue."""

from __future__ import annotations

from dataclasses import dataclass

from .models import OratsDatasetKind, OratsFrequency


@dataclass(slots=True, frozen=True)
class OratsDataset:
    name: str
    endpoint_family: str
    description: str
    kind: OratsDatasetKind
    frequency: OratsFrequency
    available_fields: tuple[str, ...]
    pagination_mode: str
    compression: tuple[str, ...]
    schema_version: str
    required_license: str
    known_limitations: tuple[str, ...]


_FIELDS = (
    "ticker",
    "tradeDate",
    "expirDate",
    "strike",
    "callPut",
    "bid",
    "ask",
    "volume",
    "openInterest",
    "iv",
    "delta",
    "gamma",
    "theta",
    "vega",
    "rho",
    "stockPrice",
)

ORATS_CATALOGUE: tuple[OratsDataset, ...] = (
    OratsDataset(
        name="options_eod",
        endpoint_family="historical/options",
        description="Representative licensed end-of-day option chain",
        kind=OratsDatasetKind.OPTION_QUOTES,
        frequency=OratsFrequency.END_OF_DAY,
        available_fields=_FIELDS,
        pagination_mode="page",
        compression=("gzip", "zip"),
        schema_version="orats-eod-fixture-v1",
        required_license="ORATS historical data license",
        known_limitations=(
            "Coverage and fields vary by license",
            "Validated only against synthetic fixture schema",
        ),
    ),
)


def get_dataset(kind: OratsDatasetKind, frequency: OratsFrequency) -> OratsDataset:
    for dataset in ORATS_CATALOGUE:
        if dataset.kind == kind and dataset.frequency == frequency:
            return dataset
    raise KeyError(f"No verified ORATS dataset for {kind.value}/{frequency.value}")
