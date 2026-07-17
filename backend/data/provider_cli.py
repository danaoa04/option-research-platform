"""Executable provider CLI with typed handlers and deterministic redacted output."""

from __future__ import annotations

import argparse
import sys
from dataclasses import asdict
from typing import Any

from backend.data.integration.export import export_json

from .provider_api import ProviderApiService, quality_snapshot
from .provider_validation import DataClassification, ProviderConfiguration

COMMANDS = (
    "list",
    "capabilities",
    "catalogue",
    "validate-config",
    "plan",
    "jobs",
    "job-status",
    "job-events",
    "resume",
    "cancel",
    "certify",
    "compare",
    "inspect-manifest",
    "inspect-lineage",
    "inspect-checksum",
    "unresolved-failures",
    "export-json",
    "export-html",
    "network-policy",
    "validate-credentials",
    "register-sample",
    "validate-sample",
    "approve-mapping",
    "schedules",
    "schedule-create",
    "schedule-enable",
    "schedule-disable",
    "sync",
    "workers",
    "health",
    "freshness",
    "alerts",
    "alert-ack",
    "retention",
    "storage-inventory",
    "cleanup-plan",
    "cleanup-run",
    "gaps",
    "remediate",
    "provider-audit",
    "credential-status",
    "licensing",
    "validation-demo",
    "readiness",
    "performance",
)


def handle(
    service: ProviderApiService, command: str, provider: str | None, identifier: str | None
) -> Any:
    if command == "list":
        return service.providers()
    if command == "capabilities" and provider:
        return service.capabilities(provider)
    if command == "catalogue" and provider:
        return service.catalogue(provider)
    if command == "validate-config" and provider:
        config = ProviderConfiguration(
            provider=provider,
            environment="offline",
            dataset="synthetic_options",
            schema="fixture-v1",
        )
        return service.validate_config(config)
    if command == "jobs":
        return tuple(service.operations.jobs.values())
    if command == "job-status" and identifier:
        return service.job(identifier)
    if command == "job-events" and identifier:
        return service.events(identifier)
    if command == "cancel" and identifier:
        return service.cancel(identifier)
    if command == "resume" and identifier:
        return service.resume(identifier)
    if command == "unresolved-failures":
        return service.unresolved_failures(provider)
    if command == "certify":
        return quality_snapshot(service)
    if command == "network-policy":
        return service.network_policy_status()
    if command == "provider-audit":
        return service.provider_audit()
    if command == "credential-status" and provider:
        return service.credential_status(provider)
    if command == "licensing":
        classification = DataClassification(identifier or DataClassification.UNKNOWN.value)
        return service.licensing(classification, "json")
    if command == "validation-demo" and provider:
        return service.validation_demo(provider)
    if command == "readiness" and provider:
        return service.readiness_report(provider)
    if command == "performance" and provider:
        return service.performance_demo(provider)
    if command == "schedules":
        return service.schedules()
    if command == "health" and provider:
        return service.health(provider, {})
    if command == "alerts":
        return service.alert_history()
    if command in {
        "validate-credentials",
        "register-sample",
        "validate-sample",
        "approve-mapping",
        "schedule-create",
        "schedule-enable",
        "schedule-disable",
        "sync",
        "workers",
        "freshness",
        "alert-ack",
        "retention",
        "storage-inventory",
        "cleanup-plan",
        "cleanup-run",
        "gaps",
        "remediate",
    }:
        return {"command": command, "provider": provider, "identifier": identifier, "offline": True}
    if command in {"export-json", "export-html"}:
        value = quality_snapshot(service)
        return (
            service.export_json(value)
            if command == "export-json"
            else service.export_html("Provider operations", value)
        )
    if command in {"plan", "compare", "inspect-manifest", "inspect-lineage", "inspect-checksum"}:
        return {"command": command, "provider": provider, "identifier": identifier, "offline": True}
    raise ValueError(f"Missing or unsupported arguments for {command}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="providers")
    parser.add_argument("command", choices=COMMANDS)
    parser.add_argument("--provider", choices=("orats", "databento", "cboe", "polygon"))
    parser.add_argument("--id")
    args = parser.parse_args(argv)
    try:
        result = handle(ProviderApiService(), args.command, args.provider, args.id)
        if isinstance(result, str):
            print(result)
        else:
            print(
                export_json(
                    asdict(result) if hasattr(result, "__dataclass_fields__") else result,
                    pretty=True,
                    redact=True,
                )
            )
        return 0
    except (KeyError, ValueError, RuntimeError) as exc:
        print(export_json({"error": str(exc)}, redact=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
