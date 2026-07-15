"""Portfolio performance and concentration analytics."""

from __future__ import annotations

from dataclasses import dataclass

from .models import CandidateInput, PortfolioAllocation, PortfolioAnalytics


@dataclass(slots=True)
class PortfolioAnalyticsEngine:
    def compute(
        self,
        candidates: tuple[CandidateInput, ...],
        allocations: tuple[PortfolioAllocation, ...],
    ) -> PortfolioAnalytics:
        by_id = {item.candidate_id: item for item in candidates}
        if not allocations:
            zero = {
                "hhi": 0.0,
                "effective_positions": 0.0,
                "effective_clusters": 0.0,
                "top_symbol": 0.0,
                "top_sector": 0.0,
                "top_strategy": 0.0,
                "greeks": 0.0,
                "expiry": 0.0,
                "volatility_regime": 0.0,
                "liquidity": 0.0,
                "model_dependency": 0.0,
            }
            return PortfolioAnalytics(
                total_return=0.0,
                cagr=0.0,
                volatility=0.0,
                sharpe=0.0,
                sortino=0.0,
                calmar=0.0,
                maximum_drawdown=0.0,
                expected_shortfall=0.0,
                downside_deviation=0.0,
                profit_factor=0.0,
                win_rate=0.0,
                time_under_water=0.0,
                capital_utilization=0.0,
                turnover=0.0,
                diversification_ratio=0.0,
                concentration_metrics=zero,
                effective_number_of_strategies=0.0,
                exposure_history={},
                strategy_contribution={},
                risk_factor_contribution={},
                regime_contribution={},
            )

        weighted_returns = [
            by_id[item.candidate_id].stats.expected_return * item.weight for item in allocations
        ]
        weighted_vol = [
            by_id[item.candidate_id].stats.volatility * item.weight for item in allocations
        ]
        weighted_shortfall = [
            by_id[item.candidate_id].stats.expected_shortfall * item.weight for item in allocations
        ]
        weighted_drawdown = [
            by_id[item.candidate_id].stats.maximum_drawdown * item.weight for item in allocations
        ]
        weighted_theta = [
            by_id[item.candidate_id].exposure.theta * item.weight for item in allocations
        ]
        total_return = sum(weighted_returns)
        volatility = sum(weighted_vol)
        expected_shortfall = sum(weighted_shortfall)
        max_drawdown = sum(weighted_drawdown)
        downside_deviation = sum(
            max(0.0, -by_id[item.candidate_id].stats.expected_return) * item.weight
            for item in allocations
        )
        sharpe = total_return / max(volatility, 1e-8)
        sortino = total_return / max(downside_deviation, 1e-8)
        calmar = total_return / max(max_drawdown, 1e-8)

        weights = [item.weight for item in allocations]
        hhi = sum(weight * weight for weight in weights)
        effective_positions = 1.0 / max(hhi, 1e-8)
        concentration = {
            "hhi": hhi,
            "effective_positions": effective_positions,
            "effective_clusters": effective_positions,
            "top_symbol": max(weights),
            "top_sector": max(weights),
            "top_strategy": max(weights),
            "greeks": max(abs(sum(weighted_theta)), abs(total_return)),
            "expiry": max(weights),
            "volatility_regime": max(weights),
            "liquidity": sum(
                by_id[item.candidate_id].exposure.liquidity_score * item.weight
                for item in allocations
            ),
            "model_dependency": sum(
                by_id[item.candidate_id].exposure.model_risk_score * item.weight
                for item in allocations
            ),
        }

        total_capital = sum(item.capital for item in allocations)
        strategy_contribution = {
            item.candidate_id: by_id[item.candidate_id].stats.expected_return * item.weight
            for item in allocations
        }
        risk_factor_contribution = {
            "delta": sum(
                by_id[item.candidate_id].exposure.delta * item.weight for item in allocations
            ),
            "gamma": sum(
                by_id[item.candidate_id].exposure.gamma * item.weight for item in allocations
            ),
            "vega": sum(
                by_id[item.candidate_id].exposure.vega * item.weight for item in allocations
            ),
            "theta": sum(
                by_id[item.candidate_id].exposure.theta * item.weight for item in allocations
            ),
        }

        regime_contribution: dict[str, float] = {}
        for allocation in allocations:
            candidate = by_id[allocation.candidate_id]
            for regime, value in candidate.stats.regime_exposure.items():
                regime_contribution[regime] = (
                    regime_contribution.get(regime, 0.0) + value * allocation.weight
                )

        win_rate = sum(1 for item in weighted_returns if item > 0.0) / len(weighted_returns)
        profit_factor = sum(item for item in weighted_returns if item > 0.0) / max(
            abs(sum(item for item in weighted_returns if item < 0.0)), 1e-8
        )

        return PortfolioAnalytics(
            total_return=total_return,
            cagr=total_return,
            volatility=volatility,
            sharpe=sharpe,
            sortino=sortino,
            calmar=calmar,
            maximum_drawdown=max_drawdown,
            expected_shortfall=expected_shortfall,
            downside_deviation=downside_deviation,
            profit_factor=profit_factor,
            win_rate=win_rate,
            time_under_water=max_drawdown,
            capital_utilization=total_capital,
            turnover=sum(
                by_id[item.candidate_id].stats.turnover * item.weight for item in allocations
            ),
            diversification_ratio=sum(abs(value) for value in weighted_returns)
            / max(abs(total_return), 1e-8),
            concentration_metrics=concentration,
            effective_number_of_strategies=effective_positions,
            exposure_history={
                "delta": [risk_factor_contribution["delta"]],
                "gamma": [risk_factor_contribution["gamma"]],
                "vega": [risk_factor_contribution["vega"]],
                "theta": [risk_factor_contribution["theta"]],
            },
            strategy_contribution=strategy_contribution,
            risk_factor_contribution=risk_factor_contribution,
            regime_contribution=regime_contribution,
        )
