from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import create_engine, select

from backend.database import (
    BacktestExecutionBrokerPolicyVersionDTO,
    BacktestExecutionCalibrationChecksumDTO,
    BacktestExecutionCalibrationDatasetDTO,
    BacktestExecutionCalibrationDriftDTO,
    BacktestExecutionCalibrationPersistenceService,
    BacktestExecutionCalibrationQueryService,
    BacktestExecutionFillQualityObservationDTO,
    BacktestExecutionPartialFillModelDTO,
    BacktestExecutionPolicyComparisonDTO,
    BacktestExecutionQualityScoreDTO,
    BacktestExecutionRealVsSimulatedDTO,
    BacktestExecutionSlippageModelDTO,
    BacktestExecutionSpreadCaptureModelDTO,
    BacktestExecutionStressTestResultDTO,
    BacktestExecutionTransactionCostPolicyDTO,
    BacktestExecutionValidationRunDTO,
    BacktestPersistenceService,
    BacktestRunDTO,
    deterministic_execution_calibration_checksum,
)
from backend.database.models import (
    BacktestExecutionFillQualityObservationRecord,
    BacktestExecutionQualityScoreRecord,
    BacktestExecutionStressTestResultRecord,
    BacktestRun,
    Base,
)
from backend.database.session import DatabaseSessionManager


def _run() -> BacktestRunDTO:
    ts = datetime(2027, 1, 15, 15, 0, tzinfo=UTC)
    return BacktestRunDTO(
        run_id="bt-exec-cal-1",
        strategy_name="execution-calibration",
        started_at=ts,
        ended_at=ts,
        configuration_json={"sprint": "7C"},
        status="completed",
        reproducibility_json={
            "event_ordering": "timestamp_priority_sequence",
            "information_set_policy": "no_look_ahead",
            "lookup_policies": {"quotes": "nearest_prior"},
            "dataset_manifests": ["execution-calibration-fixture"],
            "fill_policies": {"mode": "midpoint_with_calibration"},
            "lifecycle_policies": {"profit_target": 0.2},
        },
        checksums={"execution_calibration": "pending"},
        metadata_json={"sprint": "7C"},
        software_git_commit="deadbeef",
        schema_version="7.0",
        random_seed=7,
        created_at=ts,
    )


def test_execution_calibration_persistence_round_trip() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    manager = DatabaseSessionManager(engine)

    BacktestPersistenceService(manager).store_run(
        _run(),
        events=[],
        order_intents=[],
        fills=[],
        positions=[],
        position_legs=[],
        valuations=[],
        cash_ledger=[],
        snapshots=[],
        lifecycle_triggers=[],
        run_comparisons=[],
        scenarios=[],
        reproducibility_checksums=[],
    )

    ts = datetime(2027, 1, 15, 15, 0, tzinfo=UTC)
    service = BacktestExecutionCalibrationPersistenceService(manager)
    service.store_run_state(
        run_id="bt-exec-cal-1",
        calibration_datasets=[
            BacktestExecutionCalibrationDatasetDTO(
                dataset_id="ds-1",
                source_type="synthetic_backtest",
                provider_manifest="m1",
                broker_policy_version="generic_baseline:7C-research-v1",
                sample_count=100,
                filters_json={"symbol": "SPY"},
                metadata_json={"note": "seed"},
                created_at=ts,
            )
        ],
        fill_quality_observations=[
            BacktestExecutionFillQualityObservationDTO(
                observation_id="obs-1",
                dataset_id="ds-1",
                event_timestamp=ts,
                symbol="SPY",
                contract_identifier="SPY-202701C500",
                market_regime="normal",
                liquidity_regime="normal",
                volatility_regime="medium",
                strategy_family="iron_condors",
                fill_ratio=Decimal("0.8"),
                price_improvement=Decimal("0.01"),
                price_disimprovement=Decimal("0"),
                effective_spread=Decimal("0.08"),
                realized_spread=Decimal("0.02"),
                quoted_spread=Decimal("0.10"),
                spread_capture=Decimal("0.02"),
                slippage_vs_midpoint=Decimal("0.03"),
                slippage_vs_arrival=Decimal("0.02"),
                implementation_shortfall=Decimal("0.02"),
                cancellation_rate=Decimal("0"),
                timeout_rate=Decimal("0"),
                partial_fill_rate=Decimal("1"),
                delay_to_fill_seconds=Decimal("4"),
                residual_quantity=2,
                legging_cost=Decimal("0.25"),
                opportunity_cost=Decimal("0.1"),
                execution_cost_bps=Decimal("8.5"),
                execution_cost_dollars=Decimal("1.65"),
                metadata_json={"portfolio": "p1"},
            )
        ],
        slippage_models=[
            BacktestExecutionSlippageModelDTO(
                model_id="slip-1",
                dataset_id="ds-1",
                model_name="spread_width_dependent",
                calibrated_parameters={"spread_width_multiplier": 0.3},
                confidence_intervals={"spread_width_multiplier": [0.2, 0.4]},
                sample_size=100,
                fit_diagnostics={"rmse": 0.01},
                residual_analysis={"mean_residual": 0.0},
                regime_coverage={"market:normal": 1.0},
                warnings=[],
                validity_status="valid",
                calibrated_at=ts,
            )
        ],
        spread_capture_models=[
            BacktestExecutionSpreadCaptureModelDTO(
                model_id="spread-1",
                dataset_id="ds-1",
                model_name="spread_capture_distribution",
                calibrated_parameters={"p50": 0.02},
                confidence_intervals={"p50": [0.01, 0.03]},
                sample_size=100,
                fit_diagnostics={"capture_std": 0.01},
                residual_analysis={"mean_residual": 0.0},
                regime_coverage={"market:normal": 1.0},
                warnings=[],
                validity_status="valid",
                calibrated_at=ts,
            )
        ],
        partial_fill_models=[
            BacktestExecutionPartialFillModelDTO(
                model_id="partial-1",
                dataset_id="ds-1",
                fill_probability=Decimal("0.95"),
                expected_fill_ratio=Decimal("0.9"),
                cancellation_probability=Decimal("0.05"),
                timeout_probability=Decimal("0.02"),
                retry_probability=Decimal("0.1"),
                expected_residual_quantity=Decimal("0.5"),
                multi_leg_completion_probability=Decimal("0.85"),
                legging_exposure_duration_seconds=Decimal("12"),
                conditioned_on={"legs": 4},
                warnings=[],
                calibrated_at=ts,
            )
        ],
        transaction_cost_policies=[
            BacktestExecutionTransactionCostPolicyDTO(
                policy_id="tc-1",
                policy_name="default_cost",
                policy_version="v1",
                policy_json={"commission": 0.65},
                metadata_json={"scope": "research"},
                created_at=ts,
            )
        ],
        broker_policy_versions=[
            BacktestExecutionBrokerPolicyVersionDTO(
                policy_name="generic_baseline",
                policy_version="7C-research-v1",
                effective_date=date(2026, 7, 15),
                source_reference_metadata={"source": "internal"},
                assumptions=["deterministic"],
                supported_instruments=["equity_option"],
                unsupported_instruments=["futures_option"],
                known_differences_from_official=["not_official"],
                deprecated_versions=[],
            )
        ],
        policy_comparisons=[
            BacktestExecutionPolicyComparisonDTO(
                comparison_id="pc-1",
                event_timestamp=ts,
                left_policy="generic_baseline:v1",
                right_policy="ibkr_style:v1",
                commissions_diff=Decimal("1"),
                exchange_fees_diff=Decimal("0.2"),
                exercise_assignment_fees_diff=Decimal("0"),
                buying_power_effect_diff=Decimal("100"),
                maintenance_requirement_diff=Decimal("20"),
                interest_diff=Decimal("2"),
                borrow_cost_diff=Decimal("1"),
                total_transaction_cost_diff=Decimal("3"),
                total_return_diff=Decimal("10"),
                cagr_diff=Decimal("0.01"),
                drawdown_diff=Decimal("0.02"),
                rejected_trades_diff=1,
                margin_breaches_diff=0,
                liquidations_diff=0,
                net_performance_diff=Decimal("7"),
                ambiguity_warnings=["research_policy_not_official"],
            )
        ],
        execution_quality_scores=[
            BacktestExecutionQualityScoreDTO(
                score_id="score-1",
                event_timestamp=ts,
                symbol="SPY",
                contract_identifier="SPY-202701C500",
                total_score=Decimal("0.77"),
                confidence=Decimal("0.71"),
                component_scores={"fill_ratio": 0.8},
                component_weights={"fill_ratio": 0.1},
                warnings=[],
            )
        ],
        real_vs_simulated=[
            BacktestExecutionRealVsSimulatedDTO(
                comparison_id="rvs-1",
                event_timestamp=ts,
                symbol="SPY",
                contract_identifier="SPY-202701C500",
                simulated_fill_price=Decimal("2.05"),
                real_fill_price=Decimal("2.07"),
                expected_fill_distribution=[2.0, 2.05, 2.1],
                price_error=Decimal("-0.02"),
                cost_error=Decimal("0.15"),
                timing_error_seconds=Decimal("1.5"),
                partial_fill_error=Decimal("-0.05"),
                fee_error=Decimal("0.01"),
                policy_mismatch=True,
                warnings=["broker_policy_version_mismatch"],
            )
        ],
        validation_runs=[
            BacktestExecutionValidationRunDTO(
                validation_run_id="val-1",
                split_type="train_validation",
                train_size=70,
                validation_size=30,
                error_distribution={"validation_mean_slippage": 0.03},
                calibration_drift=Decimal("0.01"),
                parameter_drift=Decimal("0.02"),
                out_of_sample_cost_error=Decimal("0.3"),
                overconfidence_score=Decimal("0.1"),
                warnings=[],
                created_at=ts,
            )
        ],
        calibration_drift=[
            BacktestExecutionCalibrationDriftDTO(
                drift_id="drift-1",
                event_timestamp=ts,
                model_name="spread_width_dependent",
                calibration_drift=Decimal("0.01"),
                parameter_drift=Decimal("0.02"),
                diagnostics_json={"window": "2027Q1"},
            )
        ],
        stress_test_results=[
            BacktestExecutionStressTestResultDTO(
                scenario_name="doubled_spreads",
                event_timestamp=ts,
                total_cost_delta=Decimal("1.25"),
                avg_fill_ratio=Decimal("0.75"),
                avg_delay_seconds=Decimal("6.0"),
                warnings=[],
                diagnostics_json={"source": "test"},
            )
        ],
        reproducibility_checksums=[
            BacktestExecutionCalibrationChecksumDTO(
                checksum_key="execution-calibration",
                checksum_value="sha256:abc",
                metadata_json={"note": "deterministic"},
            )
        ],
    )

    query = BacktestExecutionCalibrationQueryService(manager)
    quality = query.fill_quality_history(run_id="bt-exec-cal-1", symbol="SPY")
    scores = query.execution_quality_history(run_id="bt-exec-cal-1")
    stress = query.execution_stress_tests(run_id="bt-exec-cal-1")

    with manager.session_scope() as session:
        assert session.execute(select(BacktestRun)).scalars().all()
        assert session.execute(
            select(BacktestExecutionFillQualityObservationRecord)
        ).scalars().all()
        assert session.execute(select(BacktestExecutionQualityScoreRecord)).scalars().all()
        assert session.execute(select(BacktestExecutionStressTestResultRecord)).scalars().all()

    assert len(quality) == 1
    assert len(scores) == 1
    assert len(stress) == 1


def test_execution_calibration_checksum_stability() -> None:
    ts = datetime(2027, 1, 15, 15, 0, tzinfo=UTC)
    datasets = [
        BacktestExecutionCalibrationDatasetDTO(
            dataset_id="b",
            source_type="synthetic_backtest",
            provider_manifest="m1",
            broker_policy_version="v1",
            sample_count=10,
            filters_json={},
            metadata_json={},
            created_at=ts,
        ),
        BacktestExecutionCalibrationDatasetDTO(
            dataset_id="a",
            source_type="synthetic_backtest",
            provider_manifest="m1",
            broker_policy_version="v1",
            sample_count=5,
            filters_json={},
            metadata_json={},
            created_at=ts,
        ),
    ]
    models = [
        BacktestExecutionSlippageModelDTO(
            model_id="z",
            dataset_id="b",
            model_name="fixed",
            calibrated_parameters={},
            confidence_intervals={},
            sample_size=1,
            fit_diagnostics={},
            residual_analysis={},
            regime_coverage={},
            warnings=[],
            validity_status="low_confidence",
            calibrated_at=ts,
        ),
        BacktestExecutionSlippageModelDTO(
            model_id="a",
            dataset_id="a",
            model_name="fixed",
            calibrated_parameters={},
            confidence_intervals={},
            sample_size=1,
            fit_diagnostics={},
            residual_analysis={},
            regime_coverage={},
            warnings=[],
            validity_status="low_confidence",
            calibrated_at=ts,
        ),
    ]
    left = deterministic_execution_calibration_checksum(
        run_id="bt-exec-cal-1",
        datasets=datasets,
        slippage_models=models,
    )
    right = deterministic_execution_calibration_checksum(
        run_id="bt-exec-cal-1",
        datasets=list(reversed(datasets)),
        slippage_models=list(reversed(models)),
    )
    assert left == right
