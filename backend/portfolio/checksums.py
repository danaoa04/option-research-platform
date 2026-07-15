"""Deterministic checksum helpers for portfolio allocation runs."""

from __future__ import annotations

from hashlib import sha256

from .models import PortfolioRunResult


def deterministic_portfolio_checksum(result: PortfolioRunResult) -> str:
    payload = {
        "run_id": result.run_id,
        "problem_id": result.problem.problem_id,
        "eligible": list(result.eligible_candidates),
        "rejected": [
            {"candidate_id": item.candidate_id, "reasons": list(item.reasons)}
            for item in sorted(result.rejected_candidates, key=lambda i: i.candidate_id)
        ],
        "allocations": [
            {
                "candidate_id": item.candidate_id,
                "weight": round(item.weight, 10),
                "capital": round(item.capital, 10),
                "contracts": item.contracts,
            }
            for item in sorted(result.selected_allocations, key=lambda i: i.candidate_id)
        ],
        "software_git_commit": result.problem.software_git_commit,
        "dataset_manifests": list(result.problem.dataset_manifests),
    }
    return sha256(repr(payload).encode("utf-8")).hexdigest()
