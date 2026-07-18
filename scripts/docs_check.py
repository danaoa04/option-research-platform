"""Lightweight documentation validation for Sprint 12E."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DOCS = [
    ROOT / "docs/Getting_Started.md",
    ROOT / "docs/Installation.md",
    ROOT / "docs/Quick_Start.md",
    ROOT / "docs/User_Guide.md",
    ROOT / "docs/Strategy_Builder_Guide.md",
    ROOT / "docs/Backtesting_Guide.md",
    ROOT / "docs/Optimization_Guide.md",
    ROOT / "docs/Portfolio_Guide.md",
    ROOT / "docs/Risk_Lab_Guide.md",
    ROOT / "docs/Replay_Guide.md",
    ROOT / "docs/Volatility_Guide.md",
    ROOT / "docs/Provider_Setup.md",
    ROOT / "docs/Data_Import.md",
    ROOT / "docs/Data_Certification.md",
    ROOT / "docs/Diagnostics.md",
    ROOT / "docs/Accessibility.md",
    ROOT / "docs/Keyboard_Shortcuts.md",
    ROOT / "docs/Glossary.md",
    ROOT / "docs/Known_Limitations.md",
    ROOT / "docs/Release_Notes_1.0.0-rc.1.md",
    ROOT / "docs/RC_Testing.md",
    ROOT / "docs/Support.md",
]

REQUIRED_STRINGS = {
    ROOT / "README.md": [
        "docs/Installation.md",
        "docs/Quick_Start.md",
        "docs/Provider_Setup.md",
        "docs/Backtesting_Guide.md",
        "docs/Volatility_Guide.md",
        "docs/Troubleshooting.md",
        "docs/Known_Limitations.md",
    ],
    ROOT / "docs/Installation.md": ["Apple Silicon", "unsigned", "notarized"],
    ROOT / "docs/Release_Notes_1.0.0-rc.1.md": ["1.0.0-rc.1", "unsigned", "Apple Silicon"],
    ROOT / "docs/Known_Limitations.md": [
        "Windows",
        "Linux",
        "broker connectivity",
        "order execution",
    ],
    ROOT / "docs/Support.md": [
        "App version:",
        "OS:",
        "Architecture:",
        "Release profile:",
        "Problem summary:",
        "Expected behavior:",
        "Actual behavior:",
        "Reproduction steps:",
        "Diagnostic bundle attached:",
        "Provider data involved:",
        "Reproduces in offline mode:",
    ],
}

LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _resolve_markdown_link(source: Path, href: str) -> Path | None:
    if href.startswith(("http://", "https://", "mailto:")):
        return None
    cleaned = href.split("#", 1)[0]
    if not cleaned:
        return None
    return (source.parent / cleaned).resolve()


def collect_errors() -> list[str]:
    errors: list[str] = []
    for path in REQUIRED_DOCS:
        if not path.is_file():
            errors.append(f"Missing required doc: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        if not text.lstrip().startswith("# "):
            errors.append(f"Missing top-level heading: {path.relative_to(ROOT)}")

    for path, required_values in REQUIRED_STRINGS.items():
        text = path.read_text(encoding="utf-8")
        normalized = text.lower()
        for value in required_values:
            if value.lower() not in normalized:
                errors.append(f"Missing required text in {path.relative_to(ROOT)}: {value}")

    markdown_files = [ROOT / "README.md", *ROOT.glob("docs/*.md")]
    for path in markdown_files:
        text = path.read_text(encoding="utf-8")
        for match in LINK_RE.finditer(text):
            href = match.group(1)
            target = _resolve_markdown_link(path, href)
            if target is not None and not target.exists():
                errors.append(
                    f"Broken link in {path.relative_to(ROOT)}: {href}"
                )

    return errors


def main() -> int:
    errors = collect_errors()
    if errors:
        for error in errors:
            print(error)
        return 1
    print("docs-check: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
