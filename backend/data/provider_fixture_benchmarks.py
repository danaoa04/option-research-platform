"""Opt-in deterministic benchmark boundary for Sprint 10D.2 fixture operations."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from time import perf_counter


def run_fixture_benchmarks(operations: Mapping[str, Callable[[], object]]) -> dict[str, float]:
    if os.getenv("RUN_OPT_IN_BENCHMARKS") != "1":
        raise RuntimeError("Fixture benchmarks require RUN_OPT_IN_BENCHMARKS=1")
    timings = {}
    for name in sorted(operations):
        started = perf_counter()
        operations[name]()
        timings[name] = perf_counter() - started
    return timings
