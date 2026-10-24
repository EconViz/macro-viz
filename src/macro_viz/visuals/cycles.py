"""Business-cycle visual builders using public MosaicKit layers."""

from __future__ import annotations

from bisect import bisect_left, bisect_right

from mosaickit import Canvas, FillLayer, MarkerLayer, PathLayer, TextLayer
from mosaickit.styles.nudge import Nudge

from macro_viz.cycles.models import BusinessCycleResult, TurningPointKind
from macro_viz.visuals._common import dated_series_canvas, observed_range


def _recession_layers(result: BusinessCycleResult) -> list[FillLayer]:
    low, high = observed_range((result.output, result.trend))
    layers = []
    for index, recession in enumerate(result.recessions):
        left = bisect_left(result.output.dates, recession.start)
        right = bisect_right(result.output.dates, recession.end) - 1
        if left >= len(result.output.dates) or right < 0 or left > right:
            continue
        layers.append(
            FillLayer(
                (
                    (left - 0.5, low),
                    (right + 0.5, low),
                    (right + 0.5, high),
                    (left - 0.5, high),
                ),
                id=f"macro.cycles.recession.{index}",
                role="macro.recession",
                z_index=-5,
            )
        )
    return layers


def _turning_layers(result: BusinessCycleResult) -> list[MarkerLayer | TextLayer]:
    layers: list[MarkerLayer | TextLayer] = []
    date_to_index = {period: index for index, period in enumerate(result.output.dates)}
    counts = {TurningPointKind.PEAK: 0, TurningPointKind.TROUGH: 0}
    for point in result.turning_points:
        occurrence = counts[point.kind]
        counts[point.kind] += 1
        index = date_to_index[point.period]
        root = f"macro.cycles.{point.kind.value}.{occurrence}"
        role = f"macro.turning.{point.kind.value}"
        layers.append(MarkerLayer(((index, point.value),), id=root, role=role))
        layers.append(
            TextLayer(
                (index, point.value),
                "Peak" if point.kind is TurningPointKind.PEAK else "Trough",
                id=f"{root}.label",
                role=role,
                anchor="bottom" if point.kind is TurningPointKind.PEAK else "top",
                nudge=Nudge(dy=6 if point.kind is TurningPointKind.PEAK else -6),
            )
        )
    return layers


def business_cycle_canvas(result: BusinessCycleResult, *, title: str | None = None) -> Canvas:
    """Draw output, trend, turning points, and recession shading."""
    return dated_series_canvas(
        (
            (result.output, "macro.cycles.output", "macro.series.primary", result.output.name),
            (result.trend, "macro.cycles.trend", "macro.series.trend", "Trend"),
        ),
        title=title,
        before=_recession_layers(result),
        after=_turning_layers(result),
    )


def output_gap_canvas(result: BusinessCycleResult, *, title: str | None = None) -> Canvas:
    """Draw percentage output gaps as positive and negative bars around zero."""
    bars = []
    half_width = 0.38
    for index, value in enumerate(result.output_gap.values):
        if value is None or value == 0:
            continue
        role = "macro.gap.positive" if value > 0 else "macro.gap.negative"
        direction = "positive" if value > 0 else "negative"
        bars.append(
            FillLayer(
                (
                    (index - half_width, 0),
                    (index + half_width, 0),
                    (index + half_width, value),
                    (index - half_width, value),
                ),
                id=f"macro.cycles.output.gap.{direction}.{index}",
                role=role,
            )
        )
    zero = PathLayer(
        ((0, 0), (max(len(result.output_gap.dates) - 1, 1), 0)),
        id="macro.cycles.output.gap.zero",
        role="macro.guide",
    )
    return dated_series_canvas(
        (
            (
                result.output_gap,
                "macro.cycles.output.gap",
                "macro.series.primary",
                "Output gap",
            ),
        ),
        title=title,
        include_zero=True,
        before=bars,
        after=(zero,),
    )
