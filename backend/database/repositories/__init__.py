"""Repository exports for database access patterns."""

from .market_data import (
    ContractsRepository,
    CorporateActionsRepository,
    DividendsRepository,
    EarningsRepository,
    InterestRatesRepository,
    ManifestsLineageRepository,
    QuotesRepository,
    UnderlyingPricesRepository,
)
from .optimization import OptimizationCandidateResultRepository, OptimizationRunRepository
from .reproducibility import (
    AuditRepository,
    CorporateActionNormalizationRepository,
    SnapshotRepository,
)
from .research import ResearchOpportunityRepository, ResearchRunRepository
from .validation import (
    ValidationCandidateResultRepository,
    ValidationFoldRepository,
    ValidationRunRepository,
)
from .volatility import VolatilityObservationRepository, VolatilitySliceRepository

__all__ = [
    "ContractsRepository",
    "CorporateActionsRepository",
    "DividendsRepository",
    "EarningsRepository",
    "InterestRatesRepository",
    "OptimizationCandidateResultRepository",
    "OptimizationRunRepository",
    "ValidationCandidateResultRepository",
    "ValidationFoldRepository",
    "ValidationRunRepository",
    "ManifestsLineageRepository",
    "QuotesRepository",
    "UnderlyingPricesRepository",
    "AuditRepository",
    "CorporateActionNormalizationRepository",
    "ResearchOpportunityRepository",
    "ResearchRunRepository",
    "SnapshotRepository",
    "VolatilityObservationRepository",
    "VolatilitySliceRepository",
]
