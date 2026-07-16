"""Offline-testable ORATS historical-data adapter contracts."""

from .catalogue import ORATS_CATALOGUE, OratsDataset
from .models import (
    OratsDataRequest,
    OratsDatasetKind,
    OratsFrequency,
    OratsProgress,
    OratsRequestMode,
)
from .normalization import OratsNormalizer, OratsSchemaError
from .service import OratsAdapter, OratsRunResult
from .transport import FakeOratsTransport, OratsResponse, OratsTransport

__all__ = [
    "FakeOratsTransport",
    "ORATS_CATALOGUE",
    "OratsAdapter",
    "OratsDataRequest",
    "OratsDataset",
    "OratsDatasetKind",
    "OratsFrequency",
    "OratsNormalizer",
    "OratsProgress",
    "OratsRequestMode",
    "OratsResponse",
    "OratsRunResult",
    "OratsSchemaError",
    "OratsTransport",
]
