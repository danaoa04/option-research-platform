from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select

from backend.database import (
    PortfolioAllocationDTO,
    PortfolioClusterDTO,
    PortfolioConstraintOutcomeDTO,
    PortfolioCorrelationDTO,
    PortfolioEligibleCandidateDTO,
    PortfolioPersistenceService,
    PortfolioRebalancePlanDTO,
    PortfolioRejectedCandidateDTO,
    PortfolioRiskContributionDTO,
    PortfolioRunDTO,
    PortfolioScenarioDTO,
    deterministic_portfolio_run_checksum,
)
from backend.database.models import (
    Base,
    PortfolioAllocationRecord,
    PortfolioEligibleCandidateRecord,
    PortfolioRun,
)
from backend.database.session import DatabaseSessionManager


@pytest.fixture()
def sqlite_manager() -> Iterator[DatabaseSessionManager]:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    manager = DatabaseSessionManager(engine)
    try:
        yield manager
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def _run() -> PortfolioRunDTO:
    return PortfolioRunDTO(
        run_id="portfolio-run-1",
        problem_id="problem-1",
        strategy_name="calendar_spread",
        allocation_problem={"mode": "research-only"},
        objective_definitions={"maximize": ["expected_return"]},
        constraint_definitions={"hard": ["max_portfolio_vega"]},
        correlation_policy={"kind": "strategy_return"},
        sizing_policy={"policy": "inverse_volatility"},
        rebalance_policy={"frequency": "monthly"},
        eligible_count=2,
        rejected_count=1,
        allocation_count=2,
        reserve_cash=Decimal("25000"),
        available_capital=Decimal("250000"),
        checksums={"inputs": "abc"},
        software_git_commit="deadbeef",
        schema_version="1.0",
        random_seed=11,
        dataset_manifests=[101, 102],
        warnings=["sparse correlation for candidate c"],
        failures=[],
        metadata_json={
            "allocation_problem": {"mode": "research-only"},
            "objective_definitions": {"maximize": ["expected_return"]},
            "constraint_definitions": {"hard": ["max_portfolio_vega"]},
            "correlation_policy": {"kind": "strategy_return"},
            "sizing_policy": {"policy": "inverse_volatility"},
            "rebalance_policy": {"frequency": "monthly"},
            "dataset_manifests": [101, 102],
        },
        created_at=datetime(2026, 2, 5, 14, 30, tzinfo=UTC),
    )


def test_portfolio_persistence_round_trip(sqlite_manager: DatabaseSessionManager) -> None:
    service = PortfolioPersistenceService(sqlite_manager)
    run = _run()

    row_id = service.store_run(
        run,
        eligible_candidates=[
            PortfolioEligibleCandidateDTO(
                candidate_id="a",
                validation_snapshot={"robustness": 0.8},
                exposure_snapshot={"delta": 0.2},
                stats_snapshot={"expected_return": 0.12},
                returns=[0.01, 0.02],
                pnl=[10.0, 20.0],
            )
        ],
        rejected_candidates=[
            PortfolioRejectedCandidateDTO(
                candidate_id="c",
                rejection_reasons=["minimum_robustness"],
            )
        ],
        allocations=[
            PortfolioAllocationDTO(
                candidate_id="a",
                weight=Decimal("0.5"),
                capital=Decimal("125000"),
                contracts=25,
                score=Decimal("0.88"),
            ),
            PortfolioAllocationDTO(
                candidate_id="b",
                weight=Decimal("0.4"),
                capital=Decimal("100000"),
                contracts=20,
                score=Decimal("0.85"),
            ),
        ],
        constraints=[
            PortfolioConstraintOutcomeDTO(
                constraint_name="max_portfolio_vega",
                severity="hard",
                observed=Decimal("0.8"),
                threshold=Decimal("1.0"),
                passed=True,
                reason="within bound",
                candidate_id=None,
            )
        ],
        correlations=[
            PortfolioCorrelationDTO(
                left_id="a",
                right_id="b",
                kind="strategy_return",
                value=Decimal("0.32"),
                uncertainty=Decimal("0.15"),
                effective_sample_size=48,
                sparse_warning=False,
            )
        ],
        clusters=[
            PortfolioClusterDTO(
                candidate_id="a",
                cluster_id="SYM-a|calendar|30d|medium",
                confidence=Decimal("0.7"),
                reasons=["symbol:SYM-a"],
            )
        ],
        risk_contributions=[
            PortfolioRiskContributionDTO(
                candidate_id="a",
                contribution_json={"variance_delta": 0.01},
            )
        ],
        scenarios=[
            PortfolioScenarioDTO(
                scenario_name="vol_spike",
                portfolio_return=Decimal("-0.03"),
                portfolio_drawdown=Decimal("0.12"),
                expected_shortfall=Decimal("0.15"),
                warnings=["liquidity withdrawal stress applied"],
            )
        ],
        rebalance_plan=[
            PortfolioRebalancePlanDTO(
                candidate_id="a",
                previous_weight=Decimal("0.6"),
                target_weight=Decimal("0.5"),
                delta_weight=Decimal("-0.1"),
                reason_codes=["fixed_schedule", "threshold_drift"],
                trigger="fixed_schedule",
                as_of_date=date(2026, 2, 5),
            )
        ],
    )

    with sqlite_manager.session_scope() as session:
        stored_run = session.execute(select(PortfolioRun)).scalars().one()
        stored_eligible = session.execute(select(PortfolioEligibleCandidateRecord)).scalars().all()
        stored_allocations = session.execute(select(PortfolioAllocationRecord)).scalars().all()

    assert row_id == stored_run.id
    assert stored_run.run_id == "portfolio-run-1"
    assert [item.candidate_id for item in stored_eligible] == ["a"]
    assert {item.candidate_id for item in stored_allocations} == {"a", "b"}


def test_portfolio_checksum_is_order_stable() -> None:
    run = _run()
    allocations = [
        PortfolioAllocationDTO(
            candidate_id="b",
            weight=Decimal("0.4"),
            capital=Decimal("100000"),
            contracts=20,
            score=Decimal("0.85"),
        ),
        PortfolioAllocationDTO(
            candidate_id="a",
            weight=Decimal("0.5"),
            capital=Decimal("125000"),
            contracts=25,
            score=Decimal("0.88"),
        ),
    ]

    checksum_a = deterministic_portfolio_run_checksum(run=run, allocations=allocations)
    checksum_b = deterministic_portfolio_run_checksum(
        run=run,
        allocations=list(reversed(allocations)),
    )

    assert checksum_a == checksum_b
