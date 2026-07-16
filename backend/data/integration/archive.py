"""Bounded, traversal-safe local archive extraction."""

from __future__ import annotations

import gzip
import shutil
import tarfile
import zipfile
from pathlib import Path


class UnsafeArchiveError(ValueError):
    pass


def extract_archive(
    archive: str | Path,
    destination: str | Path,
    *,
    max_files: int = 10_000,
    max_total_bytes: int = 10 * 1024**3,
) -> tuple[Path, ...]:
    """Extract known archives in deterministic order after validating every member."""
    source, target = Path(archive), Path(destination)
    target.mkdir(parents=True, exist_ok=True)
    name = source.name.lower()
    if name.endswith(".zip"):
        with zipfile.ZipFile(source) as handle:
            zip_members = sorted(handle.infolist(), key=lambda item: item.filename)
            _validate_members(
                [(m.filename, m.file_size) for m in zip_members],
                target,
                max_files,
                max_total_bytes,
            )
            for zip_member in zip_members:
                if not zip_member.is_dir():
                    output = _safe_target(target, zip_member.filename)
                    output.parent.mkdir(parents=True, exist_ok=True)
                    with handle.open(zip_member) as zip_reader, output.open("wb") as writer:
                        shutil.copyfileobj(zip_reader, writer)
    elif name.endswith((".tar.gz", ".tgz")):
        with tarfile.open(source, "r:gz") as handle:
            tar_members = sorted(
                (m for m in handle.getmembers() if m.isfile()), key=lambda item: item.name
            )
            _validate_members(
                [(m.name, m.size) for m in tar_members], target, max_files, max_total_bytes
            )
            for tar_member in tar_members:
                tar_reader = handle.extractfile(tar_member)
                if tar_reader is not None:
                    output = _safe_target(target, tar_member.name)
                    output.parent.mkdir(parents=True, exist_ok=True)
                    with tar_reader, output.open("wb") as writer:
                        shutil.copyfileobj(tar_reader, writer)
    elif name.endswith(".gz"):
        output = target / source.name.removesuffix(".gz")
        with gzip.open(source, "rb") as gzip_reader, output.open("wb") as writer:
            shutil.copyfileobj(gzip_reader, writer, length=1024 * 1024)
        if output.stat().st_size > max_total_bytes:
            output.unlink(missing_ok=True)
            raise UnsafeArchiveError("Extracted data exceeds size limit")
    else:
        raise UnsafeArchiveError(f"Unsupported archive: {source.name}")
    return tuple(sorted(path for path in target.rglob("*") if path.is_file()))


def _safe_target(root: Path, member: str) -> Path:
    output = (root / member).resolve()
    if not output.is_relative_to(root.resolve()):
        raise UnsafeArchiveError(f"Archive path traversal detected: {member}")
    return output


def _validate_members(members: list[tuple[str, int]], root: Path, count: int, size: int) -> None:
    if len(members) > count or sum(item[1] for item in members) > size:
        raise UnsafeArchiveError("Archive extraction limits exceeded")
    for name, _ in members:
        _safe_target(root, name)
