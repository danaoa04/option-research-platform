# Sprint 8 Checklist

## Sprint 8A - Complete Strategy Library Foundation

- [x] Strategy library core module added with template registry, aliasing, deprecation metadata, and deterministic serialization/checksum.
- [x] Structural validation and payoff analysis services added.
- [x] Legacy strategy compile surface preserved for existing public template names.
- [x] New API contracts added for strategy catalogue/detail/schema/validation/payoff/risk/optimizer/custom payloads.
- [x] Strategy library persistence services, repositories, DTOs, and ORM entities added.
- [x] Alembic migration `0014_strategy_library_foundation` added and tested for upgrade/downgrade.
- [x] Opt-in strategy-library benchmarks added (`RUN_STRATEGY_LIBRARY_BENCHMARKS=1`).
- [x] Deterministic tests added for foundation, persistence, migrations, benchmarks, and API contracts.
- [x] Quality gate complete: `make lint` and `make test` passing.

## Known Limitations

- Research-only implementation; no live broker/API execution coupling.
- Strategy taxonomy breadth is high, but several arbitrage variants remain intentionally marked as placeholders.
- GUI/API wiring remains contract-level in Sprint 8A; deeper product UX implementation is deferred.

## Sprint 8B Recommendations

1. Add template evolution/migration utilities for version transitions and backward-compatible parameter changes.
2. Extend optimizer contract execution with richer parameter-sweep orchestration and portfolio-level constraints.
3. Add end-to-end API handlers for catalogue/search/preview workflows using the new contract DTOs.
4. Add richer scenario bundles for earnings/dividend/volatility-regime stress replay.
