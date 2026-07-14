"""Opt-in benchmark hooks for Greeks batch calculations."""

from __future__ import annotations

import time
from dataclasses import dataclass

from .engine import GreeksEngine
from .models import GreeksRequest


@dataclass(slots=True, frozen=True)
class GreeksBenchmarkResult:
    """Single benchmark timing result for Greeks workflows."""

    name: str
    elapsed_seconds: float
    request_count: int


def benchmark_batch_runtime(
    requests: list[GreeksRequest],
    *,
    iterations: int = 1,
) -> GreeksBenchmarkResult:
    """Benchmark deterministic batch Greeks runtime over fixed inputs."""
    engine = GreeksEngine()
    started = time.perf_counter()
    for _ in range(iterations):
        engine.calculate_batch(requests)
    elapsed = time.perf_counter() - started
    return GreeksBenchmarkResult(
        name="greeks_batch_runtime",
        elapsed_seconds=elapsed,
        request_count=len(requests),
    )
