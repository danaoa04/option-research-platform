"""Opt-in deterministic ORATS adapter benchmark helper."""

from __future__ import annotations

import os
from collections.abc import Callable
from time import perf_counter
from typing import Any


def run_orats_benchmark(operation: Callable[[], Any]) -> float:
    if os.getenv("RUN_OPT_IN_BENCHMARKS") != "1":
        raise RuntimeError("ORATS benchmarks require RUN_OPT_IN_BENCHMARKS=1")
    started = perf_counter()
    operation()
    return perf_counter() - started
