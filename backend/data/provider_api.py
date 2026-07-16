"""Versioned typed service handlers for provider operations and reconciliation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from backend.data.integration.export import export_html, export_json

from .provider_operations import ProviderJobStatus, ProviderOperationsService
from .providers import CboeProvider, DatabentoProvider, OratsProvider, PolygonProvider
from .reconciliation import ProviderObservation, ReconciliationPolicy, reconcile

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
