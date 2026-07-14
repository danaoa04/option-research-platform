from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, insert, select

from backend.database import (
    AdjustmentPolicy,
    AuditEventDTO,
    AuditEventService,
    CorporateActionKnowledgePolicy,
    CorporateActionService,
    CorporateActionType,
    DatasetSnapshotDTO,
    SnapshotMutationError,
    SnapshotService,
    SymbolHistoryDTO,
)
from backend.database.exceptions import DatabaseTransactionError
from backend.database.models import (
    AdjustedOptionContractView,
    AdjustedUnderlyingPriceView,
    AuditEvent,
    Base,
    DataProvider,
    DatasetManifest,
    NormalizedCorporateAction,
    OptionContract,
    RawVendorRecord,
    SnapshotSourceManifest,
    Underlying,
    UnderlyingPrice,
)
from backend.database.session import DatabaseSessionManager


@pytest.fixture()
def sqlite_manager() -> Generator[DatabaseSessionManager]:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    manager = DatabaseSessionManager(engine)
    try:
        yield manager
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def seeded_ids(sqlite_manager: DatabaseSessionManager) -> tuple[int, int, int, int, int]:
    with sqlite_manager.session_scope() as session:
        now = datetime(2026, 1, 1, tzinfo=UTC)
        provider = DataProvider(
            name="csv",
            vendor="local",
            description="fixture",
            enabled=False,
            created_at=now,
            updated_at=now,
        )
        underlying = Underlying(symbol="SPY", name="SPY", currency="USD", active=True)
        session.add_all([provider, underlying])
        session.flush()

        manifest = DatasetManifest(
            provider_id=provider.id,
            dataset_name="options",
            dataset_version="2026.01",
            schema_version="1.0",
            symbol_scope=["SPY"],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            created_timestamp=now,
            checksum="seed",
            row_count=0,
            source_metadata={"source": "test"},
        )
        contract = OptionContract(
            provider_id=provider.id,
            provider_contract_id="SPY-C-400",
            underlying_id=underlying.id,
            option_root="SPY",
            occ_symbol="SPY260117C00400000",
            call_put="C",
            strike=Decimal("400"),
            expiration=date(2026, 1, 17),
            exercise_style="american",
            settlement_type="physical",
            multiplier=Decimal("100"),
            currency="USD",
            exchange_id=None,
            first_seen_at=now,
            last_seen_at=now,
            is_active=True,
        )
        price = UnderlyingPrice(
            id=1000,
            underlying_id=underlying.id,
            price_timestamp=datetime(2026, 1, 11, 15, 0, tzinfo=UTC),
            price=Decimal("100"),
            provider_id=provider.id,
            manifest_id=1,
        )
        session.add_all([manifest, contract])
        session.flush()
        price.manifest_id = manifest.id
        session.add(price)
        session.flush()

        return provider.id, underlying.id, manifest.id, contract.id, price.id


def _insert_action(
    sqlite_manager: DatabaseSessionManager,
    *,
    action_id: int,
    provider_id: int,
    manifest_id: int,
    underlying_id: int,
    provider_action_id: str,
    action_type: str,
    effective_date: date,
    announcement_timestamp: datetime | None,
    ratio: Decimal | None = None,
    multiplier_after: Decimal | None = None,
    deliverable_after: str | None = None,
    cash_amount: Decimal | None = None,
) -> None:
    with sqlite_manager.session_scope() as session:
        session.execute(
            insert(RawVendorRecord).values(
                id=action_id,
                provider_id=provider_id,
                entity_type="corporate_action",
                provider_record_id=provider_action_id,
                payload={"provider_action_id": provider_action_id},
                source_metadata={"provider": "fixture"},
                checksum=f"sha-{provider_action_id}",
                ingested_at=datetime(2026, 1, 1, tzinfo=UTC),
                immutable=True,
            )
        )
        session.execute(
            insert(NormalizedCorporateAction).values(
                id=action_id,
                raw_record_id=action_id,
                provider_id=provider_id,
                manifest_id=manifest_id,
                underlying_id=underlying_id,
                provider_action_id=provider_action_id,
                action_type=action_type,
                effective_date=effective_date,
                announcement_timestamp=announcement_timestamp,
                ratio=ratio,
                cash_amount=cash_amount,
                multiplier_after=multiplier_after,
                deliverable_after=deliverable_after,
                terms={"seed": True},
                source_metadata={"provider": "fixture"},
                normalized_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )


def test_adjusted_views_apply_split_and_multiplier_changes(
    sqlite_manager: DatabaseSessionManager,
    seeded_ids: tuple[int, int, int, int, int],
) -> None:
    provider_id, underlying_id, manifest_id, contract_id, _ = seeded_ids
    _insert_action(
        sqlite_manager,
        action_id=1,
        provider_id=provider_id,
        manifest_id=manifest_id,
        underlying_id=underlying_id,
        provider_action_id="split-1",
        action_type=CorporateActionType.STOCK_SPLIT.value,
        effective_date=date(2026, 1, 10),
        announcement_timestamp=datetime(2026, 1, 9, 12, 0, tzinfo=UTC),
        ratio=Decimal("2"),
    )
    _insert_action(
        sqlite_manager,
        action_id=2,
        provider_id=provider_id,
        manifest_id=manifest_id,
        underlying_id=underlying_id,
        provider_action_id="mult-1",
        action_type=CorporateActionType.MULTIPLIER_CHANGE.value,
        effective_date=date(2026, 1, 10),
        announcement_timestamp=datetime(2026, 1, 9, 12, 5, tzinfo=UTC),
        multiplier_after=Decimal("50"),
    )

    service = CorporateActionService(sqlite_manager)
    policy = AdjustmentPolicy()

    underlying_result = service.build_adjusted_underlying_view(
        underlying_id=underlying_id,
        as_of=datetime(2026, 1, 12, tzinfo=UTC),
        view_name="split-adjusted",
        policy=policy,
    )
    contract_result = service.build_adjusted_option_view(
        contract_id=contract_id,
        as_of_date=date(2026, 1, 12),
        view_name="split-adjusted",
        policy=policy,
    )

    assert underlying_result.adjusted_underlying_rows == 1
    assert contract_result.adjusted_contract_rows == 1

    with sqlite_manager.session_scope() as session:
        adjusted_underlying = session.execute(select(AdjustedUnderlyingPriceView)).scalars().one()
        adjusted_contract = session.execute(select(AdjustedOptionContractView)).scalars().one()
        assert adjusted_underlying.adjusted_price == Decimal("50")
        assert adjusted_contract.adjusted_strike == Decimal("200")
        assert adjusted_contract.adjusted_multiplier == Decimal("50")


def test_announcement_aware_policy_prevents_lookahead(
    sqlite_manager: DatabaseSessionManager,
    seeded_ids: tuple[int, int, int, int, int],
) -> None:
    provider_id, underlying_id, manifest_id, _, _ = seeded_ids
    _insert_action(
        sqlite_manager,
        action_id=10,
        provider_id=provider_id,
        manifest_id=manifest_id,
        underlying_id=underlying_id,
        provider_action_id="late-announce-split",
        action_type=CorporateActionType.STOCK_SPLIT.value,
        effective_date=date(2026, 1, 10),
        announcement_timestamp=datetime(2026, 1, 12, 9, 30, tzinfo=UTC),
        ratio=Decimal("2"),
    )

    service = CorporateActionService(sqlite_manager)
    effective_policy = AdjustmentPolicy(
        knowledge_policy=CorporateActionKnowledgePolicy.EFFECTIVE_DATE
    )
    announced_policy = AdjustmentPolicy(
        knowledge_policy=CorporateActionKnowledgePolicy.ANNOUNCEMENT_AWARE
    )

    service.build_adjusted_underlying_view(
        underlying_id=underlying_id,
        as_of=datetime(2026, 1, 11, 23, 59, tzinfo=UTC),
        view_name="effective-view",
        policy=effective_policy,
    )
    service.build_adjusted_underlying_view(
        underlying_id=underlying_id,
        as_of=datetime(2026, 1, 11, 23, 59, tzinfo=UTC),
        view_name="announcement-view",
        policy=announced_policy,
    )

    with sqlite_manager.session_scope() as session:
        rows = list(
            session.execute(
                select(AdjustedUnderlyingPriceView).where(
                    AdjustedUnderlyingPriceView.underlying_id == underlying_id
                )
            ).scalars()
        )

    by_view = {row.view_name: row for row in rows}
    assert by_view["effective-view"].adjusted_price == Decimal("50")
    assert by_view["announcement-view"].adjusted_price == Decimal("100")


def test_incomplete_action_information_emits_warning(
    sqlite_manager: DatabaseSessionManager,
    seeded_ids: tuple[int, int, int, int, int],
) -> None:
    provider_id, underlying_id, manifest_id, contract_id, _ = seeded_ids
    _insert_action(
        sqlite_manager,
        action_id=20,
        provider_id=provider_id,
        manifest_id=manifest_id,
        underlying_id=underlying_id,
        provider_action_id="missing-ratio",
        action_type=CorporateActionType.REVERSE_STOCK_SPLIT.value,
        effective_date=date(2026, 1, 10),
        announcement_timestamp=datetime(2026, 1, 9, 12, 0, tzinfo=UTC),
        ratio=None,
    )

    service = CorporateActionService(sqlite_manager)
    policy = AdjustmentPolicy()

    underlying_result = service.build_adjusted_underlying_view(
        underlying_id=underlying_id,
        as_of=datetime(2026, 1, 12, tzinfo=UTC),
        view_name="warning-view",
        policy=policy,
    )
    contract_result = service.build_adjusted_option_view(
        contract_id=contract_id,
        as_of_date=date(2026, 1, 12),
        view_name="warning-view",
        policy=policy,
    )

    assert any(w.code == "incomplete_split_information" for w in underlying_result.warnings)
    assert any(w.code == "incomplete_contract_adjustment" for w in contract_result.warnings)


def test_symbol_history_resolution(
    sqlite_manager: DatabaseSessionManager,
    seeded_ids: tuple[int, int, int, int, int],
) -> None:
    provider_id, underlying_id, _, _, _ = seeded_ids
    service = CorporateActionService(sqlite_manager)

    service.insert_raw_and_normalized(
        raw_records=[],
        normalized_actions=[],
        symbol_history=[
            SymbolHistoryDTO(
                underlying_id=underlying_id,
                old_symbol="META",
                new_symbol="META1",
                effective_date=date(2026, 1, 15),
                announcement_timestamp=datetime(2026, 1, 10, tzinfo=UTC),
                provider_id=provider_id,
                source_action_id=None,
                source_metadata={"source": "rename"},
            )
        ],
    )

    before = service.resolve_symbol_history(symbol="META", as_of_date=date(2026, 1, 14))
    after = service.resolve_symbol_history(symbol="META", as_of_date=date(2026, 1, 16))

    assert before == "META"
    assert after == "META1"


def test_snapshot_verify_compare_immutable_and_audit(
    sqlite_manager: DatabaseSessionManager,
    seeded_ids: tuple[int, int, int, int, int],
) -> None:
    provider_id, _, manifest_id, _, _ = seeded_ids
    snapshot_service = SnapshotService(sqlite_manager)
    audit_service = AuditEventService(sqlite_manager)

    first = DatasetSnapshotDTO(
        id="snap-1",
        manifest_id=manifest_id,
        provider_id=provider_id,
        schema_version="2.0",
        dataset_version="2026.01",
        git_commit="abc123",
        date_start=date(2026, 1, 1),
        date_end=date(2026, 1, 31),
        symbol_scope=["SPY"],
        row_counts={"quotes": 100},
        checksums={},
        transformation_history=[{"step": "normalize"}],
        validation_summary={"status": "ok"},
        created_at=datetime(2026, 1, 31, tzinfo=UTC),
        source_manifest_ids=[manifest_id],
    )
    digest = snapshot_service._deterministic_digest(first)
    first.checksums["snapshot_digest"] = digest

    second = DatasetSnapshotDTO(
        id="snap-2",
        manifest_id=manifest_id,
        provider_id=provider_id,
        schema_version="2.0",
        dataset_version="2026.02",
        git_commit="def456",
        date_start=date(2026, 2, 1),
        date_end=date(2026, 2, 28),
        symbol_scope=["SPY"],
        row_counts={"quotes": 120},
        checksums={"snapshot_digest": "different"},
        transformation_history=[{"step": "normalize"}, {"step": "adjust"}],
        validation_summary={"status": "ok"},
        created_at=datetime(2026, 2, 28, tzinfo=UTC),
        source_manifest_ids=[manifest_id],
    )

    snapshot_service.create_snapshot(first)
    snapshot_service.create_snapshot(second)

    is_valid, _ = snapshot_service.verify_snapshot("snap-1")
    diff = snapshot_service.compare_snapshots("snap-1", "snap-2")

    assert is_valid is True
    assert diff["comparable"] is True
    assert diff["dataset_version_changed"] is True
    assert diff["row_count_delta"]["quotes"] == 20.0

    with pytest.raises(SnapshotMutationError):
        snapshot_service.reject_snapshot_mutation("snap-1")

    with pytest.raises(DatabaseTransactionError):
        snapshot_service.create_snapshot(first)

    with sqlite_manager.session_scope() as session:
        manifests = list(
            session.execute(
                select(SnapshotSourceManifest.source_manifest_id).where(
                    SnapshotSourceManifest.snapshot_id == "snap-1"
                )
            ).scalars()
        )
    assert manifests == [manifest_id]

    audit_service.record_many(
        [
            AuditEventDTO(
                event_type="snapshot_created",
                event_timestamp=datetime(2026, 1, 31, tzinfo=UTC),
                severity="info",
                provider_id=provider_id,
                manifest_id=manifest_id,
                snapshot_id="snap-1",
                correlation_id="corr-1",
                details={"snapshot": "snap-1"},
            ),
            AuditEventDTO(
                event_type="snapshot_verify_failed",
                event_timestamp=datetime(2026, 2, 1, tzinfo=UTC),
                severity="warning",
                provider_id=provider_id,
                manifest_id=manifest_id,
                snapshot_id="snap-2",
                correlation_id="corr-2",
                details={"reason": "checksum"},
            ),
        ]
    )

    events = audit_service.list_events(event_type="snapshot_created")
    assert len(events) == 1
    assert events[0].snapshot_id == "snap-1"

    with sqlite_manager.session_scope() as session:
        count = session.execute(select(AuditEvent)).scalars().all()
    assert len(count) == 2
