"""Versioned typed service handlers for provider operations and reconciliation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from backend.data.integration.export import export_html, export_json

from .provider_monitoring import ProviderMonitoringSnapshot, calculate_monitoring
from .provider_operations import ProviderJobStatus, ProviderOperationsService
from .provider_runtime import (
    AlertService,
    NetworkPolicy,
    ProviderSchedule,
    SchedulerService,
    calculate_health,
)
from .provider_validation import (
    DataClassification,
    ProviderConfiguration,
    build_manifest,
    certify_dataset,
    credential_status,
    enforce_export_policy,
    export_decision,
    lineage_event,
    normalize_option_record,
    performance_measurements,
    provider_audit,
    readiness_report,
    validate_options,
)
from .providers import CboeProvider, DatabentoProvider, OratsProvider, PolygonProvider
from .reconciliation import (
    ConsensusResult,
    ProviderObservation,
    ReconciliationPolicy,
    consensus,
    reconcile,
)

PROVIDERS = {
    "orats": OratsProvider,
    "databento": DatabentoProvider,
    "cboe": CboeProvider,
    "polygon": PolygonProvider,
}


@dataclass(slots=True, frozen=True)
class ApiResponse:
    schema_version: str
    data: Any


class ProviderApiService:
    def __init__(self, operations: ProviderOperationsService | None = None) -> None:
        self.operations = operations or ProviderOperationsService()
        self.network_policy = NetworkPolicy()
        self.scheduler = SchedulerService()
        self.alerts = AlertService()

    def providers(self) -> ApiResponse:
        return ApiResponse("1.0.0", tuple(sorted(PROVIDERS)))

    def capabilities(self, provider: str) -> ApiResponse:
        adapter = self._provider(provider)()
        capabilities = adapter.metadata.capability_contract
        return ApiResponse("1.0.0", asdict(capabilities) if capabilities else {})

    def catalogue(self, provider: str) -> ApiResponse:
        if provider == "orats":
            from .orats.catalogue import ORATS_CATALOGUE

            data: Any = ORATS_CATALOGUE
        elif provider == "databento":
            from .databento.models import DATABENTO_CATALOGUE

            data = DATABENTO_CATALOGUE
        else:
            data = ({"provider": provider, "fixture_only": True, "licensed": False},)
        return ApiResponse("1.0.0", data)

    def create_job(self, provider: str, parameters: dict[str, Any]) -> ApiResponse:
        self._provider(provider)
        return ApiResponse("1.0.0", self.operations.create_job(provider, parameters))

    def job(self, job_id: str) -> ApiResponse:
        return ApiResponse("1.0.0", self.operations.jobs[job_id])

    def events(self, job_id: str) -> ApiResponse:
        return ApiResponse("1.0.0", self.operations.jobs[job_id].events)

    def cancel(self, job_id: str) -> ApiResponse:
        return ApiResponse("1.0.0", self.operations.cancel(job_id))

    def resume(self, job_id: str) -> ApiResponse:
        return ApiResponse("1.0.0", self.operations.resume(job_id))

    def unresolved_failures(self, provider: str | None = None) -> ApiResponse:
        return ApiResponse("1.0.0", self.operations.unresolved_failures(provider))

    def merge_preview(
        self,
        observations: tuple[ProviderObservation, ...],
        policy: ReconciliationPolicy = ReconciliationPolicy(),
    ) -> ApiResponse:
        return ApiResponse("1.0.0", reconcile(observations, policy))

    def compare(self, observations: tuple[ProviderObservation, ...]) -> ApiResponse:
        return self.merge_preview(observations)

    def consensus(self, observations: tuple[ProviderObservation, ...]) -> ApiResponse:
        result: ConsensusResult = consensus(observations)
        return ApiResponse("1.0.0", result)

    def monitoring(self, provider: str, **metrics: int) -> ApiResponse:
        snapshot: ProviderMonitoringSnapshot = calculate_monitoring(provider, **metrics)
        return ApiResponse("1.0.0", snapshot)

    def network_policy_status(self) -> ApiResponse:
        return ApiResponse("1.0.0", self.network_policy)

    def provider_audit(self) -> ApiResponse:
        return ApiResponse("1.0.0", provider_audit())

    def validate_config(self, config: ProviderConfiguration) -> ApiResponse:
        issues = config.validate()
        return ApiResponse("1.0.0", {"valid": not issues, "issues": issues})

    def credential_status(
        self, provider: str, credential_reference: str | None = None
    ) -> ApiResponse:
        self._provider(provider)
        return ApiResponse("1.0.0", credential_status(provider, credential_reference))

    def licensing(self, classification: DataClassification, requested: str) -> ApiResponse:
        return ApiResponse(
            "1.0.0",
            {
                "classification": classification.value,
                "requested_export": requested,
                "decision": export_decision(classification, requested).value,
            },
        )

    def enforce_export(self, classification: DataClassification, requested: str) -> ApiResponse:
        enforce_export_policy(classification, requested)
        return ApiResponse("1.0.0", {"allowed": True})

    def validation_demo(self, provider: str) -> ApiResponse:
        self._provider(provider)
        raw = (
            {
                "option_identifier": "SPY260116C00450000",
                "timestamp": "2026-01-15T16:00:00Z",
                "bid": "1.10",
                "ask": "1.20",
                "last": "1.15",
                "volume": "100",
                "open_interest": "1000",
                "multiplier": "100",
                "exercise_style": "american",
                "settlement_style": "physical",
                "exchange": "synthetic",
            },
        )
        records = tuple(normalize_option_record(provider, item) for item in raw)
        manifest = build_manifest(
            provider,
            "synthetic_options",
            tuple(item.raw_record for item in records),
            classification=DataClassification.SYNTHETIC,
        )
        summary = validate_options(records)
        certification = certify_dataset(provider, manifest, summary)
        lineage = lineage_event(manifest, "certification", certification.metrics)
        return ApiResponse(
            "1.0.0",
            {
                "manifest": manifest,
                "lineage": lineage,
                "validation": summary,
                "certification": certification,
            },
        )

    def readiness_report(self, provider: str) -> ApiResponse:
        demo = self.validation_demo(provider).data
        report = readiness_report(
            provider,
            configuration_valid=True,
            credentials=credential_status(provider, None),
            certification=demo["certification"],
            export_enforced=True,
            gui_available=True,
            live_validated=False,
        )
        return ApiResponse("1.0.0", report)

    def performance_demo(self, provider: str) -> ApiResponse:
        from datetime import UTC, datetime, timedelta

        self._provider(provider)
        started = datetime(2026, 7, 17, 12, tzinfo=UTC)
        finished = started + timedelta(milliseconds=25)
        return ApiResponse("1.0.0", performance_measurements(1, started, finished))

    def schedules(self) -> ApiResponse:
        values = tuple(sorted(self.scheduler.schedules.values(), key=lambda item: item.schedule_id))
        return ApiResponse("1.0.0", values)

    def create_schedule(self, schedule: ProviderSchedule) -> ApiResponse:
        self.scheduler.add(schedule)
        return ApiResponse("1.0.0", schedule)

    def health(self, provider: str, metrics: dict[str, float]) -> ApiResponse:
        return ApiResponse("1.0.0", calculate_health(provider, metrics))

    def alert_history(self) -> ApiResponse:
        values = tuple(sorted(self.alerts.alerts.values(), key=lambda item: item.fingerprint))
        return ApiResponse("1.0.0", values)

    def export_json(self, value: Any) -> str:
        return export_json(value, pretty=True, redact=True)

    def export_html(self, title: str, value: Any) -> str:
        return export_html(title, value, limitations=("Licensed coverage is not implied",))

    @staticmethod
    def _provider(provider: str) -> type[Any]:
        try:
            return PROVIDERS[provider]
        except KeyError as exc:
            raise ValueError(f"Unsupported provider: {provider}") from exc


def quality_snapshot(service: ProviderApiService) -> ApiResponse:
    jobs = tuple(service.operations.jobs.values())
    failed = sum(job.status is ProviderJobStatus.FAILED for job in jobs)
    cancelled = sum(job.status is ProviderJobStatus.CANCELLED for job in jobs)
    failures = len(service.operations.unresolved_failures())
    return ApiResponse(
        "1.0.0",
        {
            "job_count": len(jobs),
            "failure_rate": failed / len(jobs) if jobs else 0.0,
            "cancelled_count": cancelled,
            "unresolved_failures": failures,
        },
    )
