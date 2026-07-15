"""Deterministic optimization execution adapters."""

from __future__ import annotations

import pickle
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from hashlib import sha256
from time import perf_counter
from typing import Any

from .checksums import candidate_input_checksum, reconcile_checksums
from .contracts import (
    ExecutionDiagnostics,
    ExecutionMode,
)
from .engine import OptimizationEngine
from .models import Candidate, OptimizationProblem, OptimizationResult

EvaluatorFn = Callable[[OptimizationProblem, Candidate], dict[str, Any]]


@dataclass(slots=True, frozen=True)
class ExecutionRequest:
    problem: OptimizationProblem
    candidate: Candidate
    evaluator_name: str
    seed: int | None


@dataclass(slots=True)
class ExecutionResultBundle:
    result: OptimizationResult
    diagnostics: ExecutionDiagnostics


class SerializationError(RuntimeError):
    """Raised when process-pool serialization cannot be satisfied."""


@dataclass(slots=True)
class SerialExecutionAdapter:
    def run(
        self,
        *,
        engine: OptimizationEngine,
        problem: OptimizationProblem,
        evaluator: EvaluatorFn,
    ) -> ExecutionResultBundle:
        started = perf_counter()
        result = engine.run(
            problem=problem, evaluator=evaluator, execution_mode=ExecutionMode.SERIAL.value
        )
        bundle = self._diagnostics(
            problem=problem, result=result, execution_mode=ExecutionMode.SERIAL, started=started
        )
        return ExecutionResultBundle(result=result, diagnostics=bundle)

    def _diagnostics(
        self,
        *,
        problem: OptimizationProblem,
        result: OptimizationResult,
        execution_mode: ExecutionMode,
        started: float,
    ) -> ExecutionDiagnostics:
        checksum_bundle = reconcile_checksums(
            problem=problem,
            result=result,
            expected_candidate_ids=result.candidate_ordering,
        )
        return ExecutionDiagnostics(
            execution_mode=execution_mode,
            candidate_count=len(result.candidate_ordering),
            completed_count=sum(item.status.value == "succeeded" for item in result.evaluations),
            failed_count=sum(item.status.value == "failed" for item in result.evaluations),
            rejected_count=sum(item.status.value == "rejected" for item in result.evaluations),
            checksum_bundle=checksum_bundle,
            runtime_seconds=perf_counter() - started,
            metadata={"optimizer": "serial"},
        )


@dataclass(slots=True)
class ThreadPoolExecutionAdapter(SerialExecutionAdapter):
    max_workers: int = 4

    def run(
        self,
        *,
        engine: OptimizationEngine,
        problem: OptimizationProblem,
        evaluator: EvaluatorFn,
    ) -> ExecutionResultBundle:
        started = perf_counter()
        result = engine.run(
            problem=problem,
            evaluator=evaluator,
            execution_mode=ExecutionMode.THREAD_POOL.value,
            max_workers=self.max_workers,
        )
        bundle = self._diagnostics(
            problem=problem,
            result=result,
            execution_mode=ExecutionMode.THREAD_POOL,
            started=started,
        )
        return ExecutionResultBundle(result=result, diagnostics=bundle)


@dataclass(slots=True)
class ProcessPoolExecutionAdapter:
    max_workers: int = 4
    timeout_seconds: float | None = None

    def run(
        self,
        *,
        engine: OptimizationEngine,
        problem: OptimizationProblem,
        evaluator: EvaluatorFn,
    ) -> ExecutionResultBundle:
        self._ensure_serializable(problem, evaluator)
        started = perf_counter()
        candidates = engine.parameter_generator.generate_exhaustive(problem.parameter_space)
        tasks = [(index, candidate) for index, candidate in enumerate(candidates)]

        results: list[tuple[int, dict[str, Any]]] = []
        with ProcessPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {
                pool.submit(_process_worker, problem, candidate, evaluator): index
                for index, candidate in tasks
            }
            for future in as_completed(futures, timeout=self.timeout_seconds):
                index = futures[future]
                payload = future.result()
                results.append((index, payload))

        ordered_payloads = [payload for _, payload in sorted(results, key=lambda item: item[0])]
        execution_result = engine.run(
            problem=problem, evaluator=evaluator, execution_mode=ExecutionMode.SERIAL.value
        )
        checksum_bundle = reconcile_checksums(
            problem=problem,
            result=execution_result,
            expected_candidate_ids=execution_result.candidate_ordering,
        )
        diagnostics = ExecutionDiagnostics(
            execution_mode=ExecutionMode.PROCESS_POOL,
            candidate_count=len(candidates),
            completed_count=len(ordered_payloads),
            failed_count=sum(
                1 for payload in ordered_payloads if payload.get("status") == "failed"
            ),
            rejected_count=sum(
                1 for payload in ordered_payloads if payload.get("status") == "rejected"
            ),
            checksum_bundle=checksum_bundle,
            runtime_seconds=perf_counter() - started,
            metadata={"optimizer": "process_pool", "max_workers": self.max_workers},
        )
        return ExecutionResultBundle(result=execution_result, diagnostics=diagnostics)

    def _ensure_serializable(self, problem: OptimizationProblem, evaluator: EvaluatorFn) -> None:
        try:
            pickle.dumps(problem)
            pickle.dumps(evaluator)
        except Exception as exc:  # noqa: BLE001
            raise SerializationError(str(exc)) from exc


@dataclass(slots=True, frozen=True)
class DistributedExecutionAdapterContract:
    task_id: str
    candidate_id: str
    input_checksum: str
    output_checksum: str | None
    retry_policy: dict[str, Any]
    idempotency_key: str
    result_reconciliation: dict[str, Any]
    duplicate_result_handling: str
    worker_version: str
    dataset_manifest_id: int
    software_version: str
    ordering_index: int
    partial_run_recovery: bool


def _process_worker(
    problem: OptimizationProblem, candidate: Candidate, evaluator: EvaluatorFn
) -> dict[str, Any]:
    input_checksum = candidate_input_checksum(problem, candidate.candidate_id)
    payload = evaluator(problem, candidate)
    payload = dict(payload)
    payload["input_checksum"] = input_checksum
    payload["output_checksum"] = sha256(repr(payload).encode("utf-8")).hexdigest()
    return payload
