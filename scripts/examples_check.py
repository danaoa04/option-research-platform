"""Validate packaged synthetic example datasets and workspaces."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET_MARKERS = ("api_key", "secret", "token", "/Users/", "credential")


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def collect_errors() -> list[str]:
    errors: list[str] = []

    dataset_manifest_path = ROOT / "examples/provider_datasets/manifest.json"
    dataset_manifest = json.loads(
        dataset_manifest_path.read_text(encoding="utf-8")
    )
    if dataset_manifest.get("licensed_data_included") is not False:
        errors.append("Dataset manifest must declare licensed_data_included=false")
    for item in dataset_manifest["datasets"]:
        path = ROOT / item["path"]
        if not path.is_file():
            errors.append(f"Missing dataset file: {item['path']}")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in SECRET_MARKERS:
            if marker in text:
                errors.append(f"Forbidden marker {marker!r} in dataset file: {item['path']}")
        checksum = _sha256(path)
        if item["checksum"] != checksum:
            errors.append(f"Dataset checksum mismatch for {item['path']}")

    workspace_manifest_path = ROOT / "examples/workspaces/manifest.json"
    workspace_manifest = json.loads(
        workspace_manifest_path.read_text(encoding="utf-8")
    )
    if workspace_manifest.get("workspace_schema_version") != 1:
        errors.append("Workspace manifest must declare workspace_schema_version=1")
    seen_ids: set[str] = set()
    for item in workspace_manifest["workspaces"]:
        if item["id"] in seen_ids:
            errors.append(f"Duplicate workspace id in manifest: {item['id']}")
        seen_ids.add(item["id"])
        path = ROOT / item["path"]
        if not path.is_file():
            errors.append(f"Missing workspace file: {item['path']}")
            continue
        raw = path.read_text(encoding="utf-8")
        for marker in SECRET_MARKERS:
            if marker in raw:
                errors.append(f"Forbidden marker {marker!r} in workspace file: {item['path']}")
        payload = json.loads(raw)
        if payload.get("schemaVersion") != 1:
            errors.append(f"Unsupported workspace schema: {item['path']}")
        checksum = _sha256(path)
        if item["checksum"] != checksum:
            errors.append(f"Workspace checksum mismatch for {item['path']}")

    return errors


def main() -> int:
    errors = collect_errors()
    if errors:
        for error in errors:
            print(error)
        return 1
    print("examples-check: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
