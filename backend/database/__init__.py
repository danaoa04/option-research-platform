"""Database foundation package for historical options data."""

from .audit import AuditEventService
from .config import DatabaseSettings, load_database_settings
from .corporate_actions import (
    AdjustmentPolicy,
    AdjustmentRunResult,
    AdjustmentWarning,
    CorporateActionKnowledgePolicy,
    CorporateActionService,
)
from .dtos import (
    AuditEventDTO,
    CorporateActionDTO,
    CorporateActionType,
    DataLineageRecordDTO,
    DatasetManifestDTO,
    DatasetSnapshotDTO,
    DividendDTO,
    EarningsEventDTO,
    InterestRateCurveDTO,
    NormalizedCorporateActionDTO,
    OptimizationCandidateResultDTO,
    OptimizationRunDTO,
    OptionContractDTO,
    OptionQuoteDTO,
    RawVendorRecordDTO,
    ResearchOpportunityDTO,
    ResearchRunDTO,
    SymbolHistoryDTO,
    UnderlyingPriceDTO,
    VolatilityObservationDTO,
    VolatilityTimeSliceDTO,
    VolatilityTimeSliceNodeDTO,
)
from .engine import create_database_engine
from .ingestion import BulkIngestionService, ImportResult, IngestionConfig, UpsertPolicy
from .optimization import (
    OptimizationMutationError,
    OptimizationPersistenceService,
    deterministic_optimization_checksum,
)
from .query import AsOfQueryResult, HistoricalQueryService
from .research import (
    ResearchMutationError,
    ResearchPersistenceService,
    deterministic_research_checksum,
)
from .session import DatabaseSessionManager
from .snapshots import SnapshotMutationError, SnapshotService
from .validation import RecordValidator, ValidationIssue, ValidationSummary
from .volatility import (
    VolatilityPersistenceService,
    VolatilitySliceMutationError,
    deterministic_slice_checksum,
)

__all__ = [
    "DatabaseSessionManager",
    "DatabaseSettings",
    "AsOfQueryResult",
    "BulkIngestionService",
    "CorporateActionDTO",
    "CorporateActionType",
    "DataLineageRecordDTO",
    "DatasetManifestDTO",
    "DatasetSnapshotDTO",
    "DividendDTO",
    "EarningsEventDTO",
    "HistoricalQueryService",
    "ImportResult",
    "IngestionConfig",
    "InterestRateCurveDTO",
    "OptionContractDTO",
    "OptimizationCandidateResultDTO",
    "OptimizationMutationError",
    "OptimizationPersistenceService",
    "OptimizationRunDTO",
    "OptionQuoteDTO",
    "RawVendorRecordDTO",
    "ResearchOpportunityDTO",
    "ResearchRunDTO",
    "RecordValidator",
    "ResearchMutationError",
    "ResearchPersistenceService",
    "SnapshotMutationError",
    "SnapshotService",
    "SymbolHistoryDTO",
    "UnderlyingPriceDTO",
    "VolatilityObservationDTO",
    "VolatilityPersistenceService",
    "VolatilitySliceMutationError",
    "VolatilityTimeSliceDTO",
    "VolatilityTimeSliceNodeDTO",
    "UpsertPolicy",
    "ValidationIssue",
    "ValidationSummary",
    "create_database_engine",
    "load_database_settings",
    "AdjustmentPolicy",
    "AdjustmentRunResult",
    "AdjustmentWarning",
    "CorporateActionKnowledgePolicy",
    "AuditEventDTO",
    "AuditEventService",
    "CorporateActionService",
    "NormalizedCorporateActionDTO",
    "deterministic_slice_checksum",
    "deterministic_optimization_checksum",
    "deterministic_research_checksum",
]
