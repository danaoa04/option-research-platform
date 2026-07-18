"""Validate release-candidate onboarding documentation paths."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def collect_errors() -> list[str]:
    errors: list[str] = []
    quick_start = (ROOT / "docs/Quick_Start.md").read_text(encoding="utf-8")
    for phrase in [
        "strategy workspace",
        "backtesting workspace",
        "volatility workspace",
        "risk workspace",
        "Diagnostics",
    ]:
        if phrase not in quick_start:
            errors.append(f"Quick start is missing required phrase: {phrase}")

    rc_testing = (ROOT / "docs/RC_Testing.md").read_text(encoding="utf-8")
    for phrase in [
        "Install the unsigned RC",
        "Launch the app",
        "Open Diagnostics",
        "Complete the [Quick Start](Quick_Start.md) workflow",
        "Generate a redacted diagnostic bundle preview",
    ]:
        if phrase not in rc_testing:
            errors.append(f"RC testing guide is missing required phrase: {phrase}")

    app_routes = (ROOT / "frontend/src/app/App.tsx").read_text(encoding="utf-8")
    for route in ["/strategies", "/backtests", "/volatility", "/risk", "/diagnostics"]:
        if route not in app_routes:
            errors.append(f"Missing documented route in frontend app: {route}")
    return errors


def main() -> int:
    errors = collect_errors()
    if errors:
        for error in errors:
            print(error)
        return 1
    print("onboarding-check: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
