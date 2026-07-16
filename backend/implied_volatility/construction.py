"""Smile, term-structure, forward-volatility, surface, and regime construction."""

from __future__ import annotations

import math
from bisect import bisect_left
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime

from .models import (
    ExtrapolationPolicy,
    ForwardVolatilityDiagnostic,
    InterpolationMethod,
    RegimeClassificationConfig,
    RegimeClassificationResult,
    SmileAxis,
    SmileBuildConfig,
    SmileBuildResult,
    SmileNode,
    SurfaceBuildConfig,
    SurfaceBuildResult,
    SurfaceNode,
    SurfaceNodeKind,
    TermPoint,
    TermStructureConfig,
    TermStructureMetrics,
    TermStructureResult,
    VolatilityObservationRecord,
    VolatilityRegimeLabel,
)


@dataclass(slots=True)
class SmileBuilder:
    def build(
        self,
        *,
        expiration: date,
        observations: list[VolatilityObservationRecord],
        config: SmileBuildConfig,
    ) -> SmileBuildResult:
        warnings: list[str] = []
        filtered = [obs for obs in observations if obs.expiration == expiration]
        filtered = [
            obs for obs in filtered if (obs.confidence_score or 0.0) >= config.quality_floor
        ]

        if len(filtered) < config.min_points:
            warnings.append("sparse strikes for smile construction")

        grouped: dict[float, list[VolatilityObservationRecord]] = defaultdict(list)
        for obs in filtered:
            grouped[_axis_value(obs, config.axis)].append(obs)

        nodes: list[SmileNode] = []
        for x in sorted(grouped):
            rows = grouped[x]
            if len(rows) > 1:
                warnings.append(f"duplicate axis point detected at {x}")
            selected = rows[0]
            iv = selected.implied_volatility
            quality = selected.confidence_score or 0.0
            if config.deduplicate_by_average and len(rows) > 1:
                iv = sum(r.implied_volatility for r in rows) / len(rows)
                quality = sum((r.confidence_score or 0.0) for r in rows) / len(rows)
            nodes.append(
                SmileNode(
                    x=x,
                    implied_volatility=iv,
                    quality_score=quality,
                    source_observation_id=selected.observation_id,
                )
            )

        diagnostics = {
            "point_count": len(nodes),
            "interpolation": config.interpolation.value,
            "extrapolation": config.extrapolation.value,
            "quality_floor": config.quality_floor,
        }
        return SmileBuildResult(
            expiration=expiration,
            axis=config.axis,
            nodes=tuple(nodes),
            warnings=tuple(warnings),
            diagnostics=diagnostics,
        )


@dataclass(slots=True)
class SmileEvaluator:
    smile: SmileBuildResult
    config: SmileBuildConfig

    def evaluate(self, x: float) -> float | None:
        points = list(self.smile.nodes)
        if not points:
            return None

        xs = [node.x for node in points]
        ys = [node.implied_volatility for node in points]

        if x < xs[0] or x > xs[-1]:
            if self.config.extrapolation == ExtrapolationPolicy.NONE:
                return None
            if self.config.extrapolation == ExtrapolationPolicy.FLAT:
                return ys[0] if x < xs[0] else ys[-1]
            return (
                _linear(xs[0], ys[0], xs[1], ys[1], x)
                if x < xs[0]
                else _linear(xs[-2], ys[-2], xs[-1], ys[-1], x)
            )

        idx = bisect_left(xs, x)
        if idx <= 0:
            return ys[0]
        if idx >= len(xs):
            return ys[-1]
        if self.config.interpolation == InterpolationMethod.MONOTONE_CUBIC and len(xs) >= 3:
            return _monotone_cubic(xs, ys, x)
        return _linear(xs[idx - 1], ys[idx - 1], xs[idx], ys[idx], x)


@dataclass(slots=True)
class TermStructureBuilder:
    def build(
        self,
        smiles: list[SmileBuildResult],
        *,
        valuation_date: date,
        target_x: float,
        config: TermStructureConfig,
    ) -> TermStructureResult:
        warnings: list[str] = []
        points: list[TermPoint] = []
        forward_diagnostics: list[ForwardVolatilityDiagnostic] = []

        for smile in sorted(smiles, key=lambda row: row.expiration):
            tenor_days = max((smile.expiration - valuation_date).days, 0)
            evaluator = SmileEvaluator(smile=smile, config=SmileBuildConfig(axis=smile.axis))
            iv = evaluator.evaluate(target_x)
            if iv is None:
                warnings.append(f"no interpolation value at tenor={tenor_days}")
                continue
            mean_quality = (
                sum(node.quality_score for node in smile.nodes) / len(smile.nodes)
                if smile.nodes
                else 0.0
            )
            points.append(
                TermPoint(
                    tenor_days=tenor_days,
                    implied_volatility=iv,
                    quality_score=mean_quality,
                )
            )

        if len(points) < 2:
            warnings.append("sparse tenor coverage")
            empty_metrics = TermStructureMetrics(
                front_back_difference=0.0,
                front_back_ratio=1.0,
                annualized_slope=0.0,
                curvature=0.0,
                tenor_normalized_slope=0.0,
                local_forward_variance=None,
                forward_implied_volatility=None,
            )
            return TermStructureResult(
                points=tuple(points),
                metrics=empty_metrics,
                classification=VolatilityRegimeLabel.MIXED.value,
                warnings=tuple(warnings),
            )

        points = sorted(points, key=lambda row: row.tenor_days)
        front = points[0]
        back = points[-1]
        tenor_span_years = max((back.tenor_days - front.tenor_days) / 365.0, 1e-8)

        diff = back.implied_volatility - front.implied_volatility
        ratio = back.implied_volatility / max(front.implied_volatility, 1e-8)
        slope = diff / tenor_span_years
        tenor_normalized_slope = diff / max(back.tenor_days - front.tenor_days, 1)

        curvature = 0.0
        if len(points) >= 3:
            mid = points[len(points) // 2]
            curvature = (
                back.implied_volatility - 2.0 * mid.implied_volatility + front.implied_volatility
            )

        for idx in range(len(points) - 1):
            diag = compute_forward_volatility(
                start_tenor_days=points[idx].tenor_days,
                end_tenor_days=points[idx + 1].tenor_days,
                start_iv=points[idx].implied_volatility,
                end_iv=points[idx + 1].implied_volatility,
            )
            forward_diagnostics.append(diag)
            if not diag.valid:
                warnings.append(diag.reason or "invalid forward variance")

        local_forward = forward_diagnostics[0].forward_variance if forward_diagnostics else None
        local_forward_iv = (
            forward_diagnostics[0].forward_volatility if forward_diagnostics else None
        )

        monotonic_signs = [
            math.copysign(1.0, points[i + 1].implied_volatility - points[i].implied_volatility)
            for i in range(len(points) - 1)
            if abs(points[i + 1].implied_volatility - points[i].implied_volatility)
            > config.monotonic_tolerance
        ]
        if len(set(monotonic_signs)) > 1:
            classification = VolatilityRegimeLabel.MIXED.value
        elif abs(slope) <= config.flat_threshold:
            classification = VolatilityRegimeLabel.FLAT.value
        elif slope > 0.0:
            classification = VolatilityRegimeLabel.CONTANGO.value
        else:
            classification = VolatilityRegimeLabel.BACKWARDATION.value

        metrics = TermStructureMetrics(
            front_back_difference=diff,
            front_back_ratio=ratio,
            annualized_slope=slope,
            curvature=curvature,
            tenor_normalized_slope=tenor_normalized_slope,
            local_forward_variance=local_forward,
            forward_implied_volatility=local_forward_iv,
        )
        return TermStructureResult(
            points=tuple(points),
            metrics=metrics,
            classification=classification,
            warnings=tuple(warnings),
            forward_diagnostics=tuple(forward_diagnostics),
        )


@dataclass(slots=True)
class SurfaceBuilder:
    def build(
        self,
        *,
        symbol: str,
        valuation_timestamp: datetime,
        observations: list[VolatilityObservationRecord],
        config: SurfaceBuildConfig,
    ) -> SurfaceBuildResult:
        warnings: list[str] = []
        nodes: list[SurfaceNode] = []

        grouped: dict[date, list[VolatilityObservationRecord]] = defaultdict(list)
        for obs in observations:
            grouped[obs.expiration].append(obs)

        for expiry, bucket in sorted(grouped.items(), key=lambda item: item[0]):
            tenor_days = max((expiry - valuation_timestamp.date()).days, 0)
            for obs in bucket:
                x = _axis_value(obs, config.smile_axis)
                quality = obs.confidence_score or 0.0
                if config.include_raw_nodes:
                    nodes.append(
                        SurfaceNode(
                            tenor_days=tenor_days,
                            x=x,
                            implied_volatility=obs.implied_volatility,
                            node_kind=SurfaceNodeKind.RAW,
                            quality_score=quality,
                            provenance={
                                "observation_id": obs.observation_id,
                                "quote_source": obs.quote_source.value,
                            },
                        )
                    )
                if quality >= config.quality_floor:
                    nodes.append(
                        SurfaceNode(
                            tenor_days=tenor_days,
                            x=x,
                            implied_volatility=obs.implied_volatility,
                            node_kind=SurfaceNodeKind.CLEANED,
                            quality_score=quality,
                            provenance={
                                "observation_id": obs.observation_id,
                                "quality_score": quality,
                            },
                        )
                    )

        cleaned = [node for node in nodes if node.node_kind == SurfaceNodeKind.CLEANED]
        if len(cleaned) < 4:
            warnings.append("sparse cleaned nodes for interpolation")

        interpolated: list[SurfaceNode] = []
        by_tenor: dict[int, list[SurfaceNode]] = defaultdict(list)
        for node in cleaned:
            by_tenor[node.tenor_days].append(node)

        for tenor_days, tenor_nodes in sorted(by_tenor.items()):
            xs = sorted({node.x for node in tenor_nodes})
            if len(xs) < 2:
                continue
            for left, right in zip(xs[:-1], xs[1:], strict=False):
                x_mid = 0.5 * (left + right)
                left_node = next(node for node in tenor_nodes if node.x == left)
                right_node = next(node for node in tenor_nodes if node.x == right)
                iv_mid = _linear(
                    left,
                    left_node.implied_volatility,
                    right,
                    right_node.implied_volatility,
                    x_mid,
                )
                interpolated.append(
                    SurfaceNode(
                        tenor_days=tenor_days,
                        x=x_mid,
                        implied_volatility=iv_mid,
                        node_kind=SurfaceNodeKind.INTERPOLATED,
                        quality_score=min(left_node.quality_score, right_node.quality_score),
                        provenance={
                            "left": left_node.provenance,
                            "right": right_node.provenance,
                            "method": config.interpolation.value,
                        },
                    )
                )

        all_nodes = nodes + interpolated
        diagnostics = {
            "raw_nodes": len([node for node in all_nodes if node.node_kind == SurfaceNodeKind.RAW]),
            "cleaned_nodes": len(
                [node for node in all_nodes if node.node_kind == SurfaceNodeKind.CLEANED]
            ),
            "interpolated_nodes": len(interpolated),
            "quality_floor": config.quality_floor,
        }
        return SurfaceBuildResult(
            symbol=symbol,
            valuation_timestamp=valuation_timestamp,
            nodes=tuple(all_nodes),
            warnings=tuple(warnings),
            diagnostics=diagnostics,
        )


@dataclass(slots=True)
class RegimeClassifier:
    def classify(
        self,
        *,
        term_structure: TermStructureResult,
        realized_volatility: float | None,
        config: RegimeClassificationConfig,
        earnings_front_elevation: float | None = None,
        prior_atm_iv: float | None = None,
    ) -> RegimeClassificationResult:
        labels: list[VolatilityRegimeLabel] = []
        metadata: dict[str, float | str | None] = {
            "term_classification": term_structure.classification,
            "realized_volatility": realized_volatility,
        }

        atm_iv = term_structure.points[0].implied_volatility if term_structure.points else None
        if atm_iv is not None:
            if atm_iv < config.iv_low_threshold:
                labels.append(VolatilityRegimeLabel.LOW_IV)
            elif atm_iv > config.iv_high_threshold:
                labels.append(VolatilityRegimeLabel.HIGH_IV)
            else:
                labels.append(VolatilityRegimeLabel.MEDIUM_IV)

        if realized_volatility is not None:
            if realized_volatility < config.realized_low_threshold:
                labels.append(VolatilityRegimeLabel.LOW_REALIZED)
            elif realized_volatility > config.realized_high_threshold:
                labels.append(VolatilityRegimeLabel.HIGH_REALIZED)
            else:
                labels.append(VolatilityRegimeLabel.MEDIUM_REALIZED)

        if term_structure.classification == VolatilityRegimeLabel.CONTANGO.value:
            labels.append(VolatilityRegimeLabel.CONTANGO)
        elif term_structure.classification == VolatilityRegimeLabel.BACKWARDATION.value:
            labels.append(VolatilityRegimeLabel.BACKWARDATION)
        elif term_structure.classification == VolatilityRegimeLabel.FLAT.value:
            labels.append(VolatilityRegimeLabel.FLAT)
        else:
            labels.append(VolatilityRegimeLabel.MIXED)

        slope = term_structure.metrics.annualized_slope
        if abs(slope) >= config.slope_steep_threshold:
            labels.append(VolatilityRegimeLabel.STEEP)

        if (
            earnings_front_elevation is not None
            and earnings_front_elevation > config.event_front_elevation_threshold
        ):
            labels.append(VolatilityRegimeLabel.EARNINGS_ELEVATION)
            if slope < 0.0:
                labels.append(VolatilityRegimeLabel.INVERTED_EVENT)

        if atm_iv is not None and prior_atm_iv is not None:
            if atm_iv > prior_atm_iv:
                labels.append(VolatilityRegimeLabel.VOL_EXPANSION)
            elif atm_iv < prior_atm_iv:
                labels.append(VolatilityRegimeLabel.VOL_CONTRACTION)

        confidence = _confidence(term_structure)
        return RegimeClassificationResult(
            labels=tuple(dict.fromkeys(labels)),
            confidence=confidence,
            metadata=metadata,
        )


def compute_forward_volatility(
    *,
    start_tenor_days: int,
    end_tenor_days: int,
    start_iv: float,
    end_iv: float,
) -> ForwardVolatilityDiagnostic:
    if end_tenor_days <= start_tenor_days:
        return ForwardVolatilityDiagnostic(
            start_tenor_days=start_tenor_days,
            end_tenor_days=end_tenor_days,
            start_iv=start_iv,
            end_iv=end_iv,
            forward_variance=None,
            forward_volatility=None,
            valid=False,
            reason="invalid tenor ordering",
        )

    t1 = start_tenor_days / 365.0
    t2 = end_tenor_days / 365.0
    total_var1 = max(start_iv, 0.0) ** 2 * t1
    total_var2 = max(end_iv, 0.0) ** 2 * t2

    forward_var = (total_var2 - total_var1) / max(t2 - t1, 1e-12)
    if forward_var < 0.0:
        return ForwardVolatilityDiagnostic(
            start_tenor_days=start_tenor_days,
            end_tenor_days=end_tenor_days,
            start_iv=start_iv,
            end_iv=end_iv,
            forward_variance=forward_var,
            forward_volatility=None,
            valid=False,
            reason="negative forward variance",
        )

    forward_vol = math.sqrt(forward_var)
    return ForwardVolatilityDiagnostic(
        start_tenor_days=start_tenor_days,
        end_tenor_days=end_tenor_days,
        start_iv=start_iv,
        end_iv=end_iv,
        forward_variance=forward_var,
        forward_volatility=forward_vol,
        valid=True,
    )


def _axis_value(observation: VolatilityObservationRecord, axis: SmileAxis) -> float:
    if axis == SmileAxis.STRIKE:
        return observation.strike
    if axis == SmileAxis.MONEYNESS:
        return observation.moneyness
    if axis == SmileAxis.LOG_MONEYNESS:
        return math.log(max(observation.moneyness, 1e-12))
    if axis == SmileAxis.DELTA:
        return observation.delta if observation.delta is not None else 0.0
    return (
        observation.forward_moneyness
        if observation.forward_moneyness is not None
        else observation.moneyness
    )


def _linear(x0: float, y0: float, x1: float, y1: float, x: float) -> float:
    if x1 == x0:
        return y0
    w = (x - x0) / (x1 - x0)
    return y0 + w * (y1 - y0)


def _monotone_cubic(xs: list[float], ys: list[float], x: float) -> float:
    idx = bisect_left(xs, x)
    idx = min(max(idx, 1), len(xs) - 1)
    x0, x1 = xs[idx - 1], xs[idx]
    y0, y1 = ys[idx - 1], ys[idx]
    h = x1 - x0
    if h == 0.0:
        return y0

    m = (y1 - y0) / h
    if idx - 2 >= 0:
        m0 = (ys[idx - 1] - ys[idx - 2]) / max(xs[idx - 1] - xs[idx - 2], 1e-12)
    else:
        m0 = m
    if idx + 1 < len(xs):
        m1 = (ys[idx + 1] - ys[idx]) / max(xs[idx + 1] - xs[idx], 1e-12)
    else:
        m1 = m

    d0 = _harmonic_mean_if_same_sign(m0, m)
    d1 = _harmonic_mean_if_same_sign(m, m1)

    t = (x - x0) / h
    h00 = (2 * t**3) - (3 * t**2) + 1
    h10 = (t**3) - (2 * t**2) + t
    h01 = (-2 * t**3) + (3 * t**2)
    h11 = (t**3) - (t**2)

    return h00 * y0 + h10 * h * d0 + h01 * y1 + h11 * h * d1


def _harmonic_mean_if_same_sign(a: float, b: float) -> float:
    if a == 0.0 or b == 0.0 or (a > 0.0) != (b > 0.0):
        return 0.0
    return 2.0 * a * b / (a + b)


def _confidence(term_structure: TermStructureResult) -> float:
    if not term_structure.points:
        return 0.0
    base = sum(point.quality_score for point in term_structure.points) / len(term_structure.points)
    penalty = min(len(term_structure.warnings) * 0.05, 0.5)
    return max(0.0, min(1.0, base - penalty))
