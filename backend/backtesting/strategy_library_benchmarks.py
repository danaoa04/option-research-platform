"""Opt-in deterministic benchmarks for Sprint 8A strategy library workflows."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from time import perf_counter

from .strategy_library import (
    LegDirection,
    LegKind,
    StrategyPayoffAnalyzer,
    StrategySelectedLeg,
    StrategyStructureValidator,
    StrategyTemplatePluginMetadata,
    default_strategy_template_registry,
    deterministic_strategy_library_checksum,
)


@dataclass(slots=True, frozen=True)
class StrategyLibraryBenchmarkResult:
    name: str
    input_size: int
    elapsed_seconds: float


@dataclass(slots=True)
class StrategyLibraryBenchmarkRunner:
    def run_all(self) -> list[StrategyLibraryBenchmarkResult]:
        if os.getenv("RUN_STRATEGY_LIBRARY_BENCHMARKS", "0") != "1":
            return []
        registry = default_strategy_template_registry()
        identifiers = [
            item.canonical_identifier for item in registry.discover(include_deprecated=True)
        ]
        return [
            self._registry_lookup_benchmark(registry, identifiers),
            self._template_compile_benchmark(registry, identifiers),
            self._validation_benchmark(registry),
            self._payoff_grid_benchmark(registry),
            self._custom_compile_benchmark(registry),
            self._serialization_benchmark(registry),
            self._plugin_discovery_benchmark(registry),
            self._query_like_benchmark(registry),
            self._large_catalogue_benchmark(),
        ]

    def _registry_lookup_benchmark(
        self, registry, identifiers: list[str]
    ) -> StrategyLibraryBenchmarkResult:
        start = perf_counter()
        for identifier in identifiers:
            registry.resolve(identifier)
        elapsed = perf_counter() - start
        return StrategyLibraryBenchmarkResult("registry_lookup", len(identifiers), elapsed)

    def _template_compile_benchmark(
        self, registry, identifiers: list[str]
    ) -> StrategyLibraryBenchmarkResult:
        start = perf_counter()
        for identifier in identifiers[:50]:
            registry.resolve(identifier).compile_generic_definition()
        elapsed = perf_counter() - start
        return StrategyLibraryBenchmarkResult(
            "template_compile", min(50, len(identifiers)), elapsed
        )

    def _validation_benchmark(self, registry) -> StrategyLibraryBenchmarkResult:
        template = registry.resolve("vertical.bull_call_spread")
        validator = StrategyStructureValidator()
        legs = (
            StrategySelectedLeg(
                label="long_call",
                leg_kind=LegKind.CALL,
                direction=LegDirection.BUY,
                quantity=1,
                strike=500.0,
                expiration=date(2027, 1, 15),
                option_type=None,
                premium=5.0,
                underlying="SPY",
                exercise_style=None,
                settlement_style=None,
                multiplier=100,
                liquidity_score=0.9,
                quote_quality=0.9,
            ),
            StrategySelectedLeg(
                label="short_call",
                leg_kind=LegKind.CALL,
                direction=LegDirection.SELL,
                quantity=1,
                strike=510.0,
                expiration=date(2027, 1, 15),
                option_type=None,
                premium=2.0,
                underlying="SPY",
                exercise_style=None,
                settlement_style=None,
                multiplier=100,
                liquidity_score=0.9,
                quote_quality=0.9,
            ),
        )
        start = perf_counter()
        for _ in range(500):
            validator.validate(template=template, selected_legs=legs)
        elapsed = perf_counter() - start
        return StrategyLibraryBenchmarkResult("validation", 500, elapsed)

    def _payoff_grid_benchmark(self, registry) -> StrategyLibraryBenchmarkResult:
        template = registry.resolve("vertical.bull_call_spread")
        analyzer = StrategyPayoffAnalyzer()
        legs = (
            StrategySelectedLeg(
                label="long_call",
                leg_kind=LegKind.CALL,
                direction=LegDirection.BUY,
                quantity=1,
                strike=500.0,
                expiration=date(2027, 1, 15),
                option_type=None,
                premium=5.0,
                underlying="SPY",
                exercise_style=None,
                settlement_style=None,
                multiplier=100,
            ),
            StrategySelectedLeg(
                label="short_call",
                leg_kind=LegKind.CALL,
                direction=LegDirection.SELL,
                quantity=1,
                strike=510.0,
                expiration=date(2027, 1, 15),
                option_type=None,
                premium=2.0,
                underlying="SPY",
                exercise_style=None,
                settlement_style=None,
                multiplier=100,
            ),
        )
        grid = tuple(float(item) for item in range(450, 551))
        start = perf_counter()
        analyzer.summarize(template=template, selected_legs=legs, price_grid=grid)
        elapsed = perf_counter() - start
        return StrategyLibraryBenchmarkResult("payoff_grid_generation", len(grid), elapsed)

    def _custom_compile_benchmark(self, registry) -> StrategyLibraryBenchmarkResult:
        template = registry.resolve("custom.custom_multi_leg")
        start = perf_counter()
        for _ in range(300):
            template.compile_generic_definition(metadata={"custom": True})
        elapsed = perf_counter() - start
        return StrategyLibraryBenchmarkResult("custom_multi_leg_compile", 300, elapsed)

    def _serialization_benchmark(self, registry) -> StrategyLibraryBenchmarkResult:
        templates = tuple(
            registry.resolve(item.canonical_identifier) for item in registry.discover()
        )
        start = perf_counter()
        _ = deterministic_strategy_library_checksum(templates=templates)
        elapsed = perf_counter() - start
        return StrategyLibraryBenchmarkResult("template_serialization", len(templates), elapsed)

    def _plugin_discovery_benchmark(self, registry) -> StrategyLibraryBenchmarkResult:
        plugin = StrategyTemplatePluginMetadata(
            plugin_name="bench",
            plugin_version="1.0.0",
            api_version="8A-v1",
            namespace="bench",
            allow_overrides=False,
        )
        extra = registry.resolve("directional.long_call")
        clone = type(extra)(
            name="plugin_long_call",
            canonical_identifier="bench.plugin_long_call",
            version=extra.version,
            aliases=(),
            family=extra.family,
            legs=extra.legs,
            entry_requirements=extra.entry_requirements,
            compatibility=extra.compatibility,
            risk_classification=extra.risk_classification,
            optimizer_contract=extra.optimizer_contract,
            known_limitations=extra.known_limitations,
            metadata=extra.metadata,
            deprecation=extra.deprecation,
        )
        start = perf_counter()
        registry.register_plugin_templates(metadata=plugin, templates=(clone,))
        out = registry.discover(include_deprecated=True)
        elapsed = perf_counter() - start
        return StrategyLibraryBenchmarkResult("plugin_discovery", len(out), elapsed)

    def _query_like_benchmark(self, registry) -> StrategyLibraryBenchmarkResult:
        start = perf_counter()
        _ = registry.discover(family=registry.resolve("vertical.bull_call_spread").family)
        elapsed = perf_counter() - start
        return StrategyLibraryBenchmarkResult("strategy_query_performance", 1, elapsed)

    def _large_catalogue_benchmark(self) -> StrategyLibraryBenchmarkResult:
        registry = default_strategy_template_registry()
        base = registry.resolve("directional.long_call")
        start = perf_counter()
        for idx in range(250):
            clone = type(base)(
                name=f"clone_{idx}",
                canonical_identifier=f"bench.clone_{idx}",
                version=base.version,
                aliases=(f"c{idx}",),
                family=base.family,
                legs=base.legs,
                entry_requirements=base.entry_requirements,
                compatibility=base.compatibility,
                risk_classification=base.risk_classification,
                optimizer_contract=base.optimizer_contract,
                known_limitations=base.known_limitations,
                metadata=base.metadata,
                deprecation=base.deprecation,
            )
            registry.register(clone)
        _ = registry.discover(include_deprecated=True)
        elapsed = perf_counter() - start
        return StrategyLibraryBenchmarkResult("large_template_catalogue", 250, elapsed)
