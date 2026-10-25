"""Business-cycle visual builders using public MosaicKit layers."""

from __future__ import annotations

from bisect import bisect_left, bisect_right

from mosaickit import Canvas, FillLayer, MarkerLayer, PointLabelLayer

from macro_viz.cycles.models import BusinessCycleResult, TurningPointKind
from macro_viz.i18n import text
from macro_viz.visuals._kit import DEFAULT_MARKS, nice_bounds
from macro_viz.visuals._series import dated_series_canvas, observed_range

BAR_HALF_WIDTH = 0.38
"""Half the width of an output-gap bar, in observation units."""


def _recession_layers(result: BusinessCycleResult, y_range: tuple[float, float]) -> list[FillLayer]:
    low, high = y_range
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


def _turning_layers(result: BusinessCycleResult) -> list[MarkerLayer | PointLabelLayer]:
    layers: list[MarkerLayer | PointLabelLayer] = []
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
            PointLabelLayer(
                (index, point.value),
                text(f"label.{point.kind.value}"),
                id=f"{root}.label",
                role=role,
            )
        )
    return layers


def business_cycle_canvas(
    result: BusinessCycleResult, *, title: str | None = None, **options: object
) -> Canvas:
    """Draw output, trend, turning points, and recession shading."""
    low, high = observed_range((result.output, result.trend))
    count = int(options.get("value_marks_count", DEFAULT_MARKS))  # type: ignore[call-overload]
    y_low, y_high, _ = nice_bounds(low, high, count)
    return dated_series_canvas(
        (
            (result.output, "macro.cycles.output", "macro.series.secondary"),
            (result.trend, "macro.cycles.trend", "macro.series.trend"),
        ),
        title=title,
        before=_recession_layers(result, (y_low, y_high)),
        after=_turning_layers(result),
        **options,  # type: ignore[arg-type]
    )


def output_gap_canvas(
    result: BusinessCycleResult, *, title: str | None = None, **options: object
) -> Canvas:
    """Draw percentage output gaps as positive and negative bars around a zero line."""
    bars = []
    for index, value in enumerate(result.output_gap.values):
        if value is None or value == 0:
            continue
        role = "macro.gap.positive" if value > 0 else "macro.gap.negative"
        direction = "positive" if value > 0 else "negative"
        bars.append(
            FillLayer(
                (
                    (index - BAR_HALF_WIDTH, 0),
                    (index + BAR_HALF_WIDTH, 0),
                    (index + BAR_HALF_WIDTH, value),
                    (index - BAR_HALF_WIDTH, value),
                ),
                id=f"macro.cycles.output.gap.{direction}.{index}",
                role=role,
            )
        )
    options.setdefault("include_zero", True)
    return dated_series_canvas(
        ((result.output_gap, "macro.cycles.output.gap", "macro.series.secondary"),),
        title=title,
        before=bars,
        **options,  # type: ignore[arg-type]
    )
