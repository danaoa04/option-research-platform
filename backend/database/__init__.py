"""Database foundation package for historical options data."""

from .config import DatabaseSettings, load_database_settings
from .dtos import (
    CorporateActionDTO,
    DataLineageRecordDTO,
    DatasetManifestDTO,
    DividendDTO,
    EarningsEventDTO,
    InterestRateCurveDTO,
    OptionContractDTO,
    OptionQuoteDTO,
    UnderlyingPriceDTO,
)
from .engine import create_database_engine
from .ingestion import BulkIngestionService, ImportResult, IngestionConfig, UpsertPolicy
from .query import AsOfQueryResult, HistoricalQueryService
from .session import DatabaseSessionManager
from .validation import RecordValidator, ValidationIssue, ValidationSummary

__all__ = [
    "DatabaseSessionManager",
    "DatabaseSettings",
    "AsOfQueryResult",
    "BulkIngestionService",
    "CorporateActionDTO",
    "DataLineageRecordDTO",
    "DatasetManifestDTO",
    "DividendDTO",
    "EarningsEventDTO",
    "HistoricalQueryService",
    "ImportResult",
    "IngestionConfig",
    "InterestRateCurveDTO",
    "OptionContractDTO",
    "OptionQuoteDTO",
    "RecordValidator",
    "UnderlyingPriceDTO",
    "UpsertPolicy",
    "ValidationIssue",
    "ValidationSummary",
    "create_database_engine",
    "load_database_settings",
]
