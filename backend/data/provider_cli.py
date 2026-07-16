"""Executable provider CLI with typed handlers and deterministic redacted output."""

from __future__ import annotations

import argparse
import sys
from dataclasses import asdict
from typing import Any

from backend.data.integration.export import export_json

from .provider_api import ProviderApiService, quality_snapshot

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
        return {"provider": provider, "offline_fixture": True, "credentials_required": False}
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
