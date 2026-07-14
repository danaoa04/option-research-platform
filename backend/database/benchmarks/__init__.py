"""Opt-in benchmarks for database ingestion and query workloads."""

from .runtime import BenchmarkResult, run_database_benchmarks

__all__ = ["BenchmarkResult", "run_database_benchmarks"]
