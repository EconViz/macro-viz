"""Dated line charts with arrowed axes, rounded value marks, and direct series names."""

from __future__ import annotations

import math
from collections.abc import Sequence

from mosaickit import AxisMarkLayer, Canvas, Layer, PathLayer

from macro_viz.errors import ValidationError
from macro_viz.series import TimeSeries
from macro_viz.visuals._kit import (
    DEFAULT_MARKS,
    axes_layers,
    canvas_spec,
    direct_label,
    new_canvas,
    nice_bounds,
    tick_values,
    title_layer,
    value_marks,
)

SeriesSpec = tuple[TimeSeries, str, str]
"""A series, its layer id, and its theme role; the series name is its direct label."""

SERIES_WIDTH = 7.0
SERIES_HEIGHT = 4.5
"""Default canvas size in inches of a dated chart (``width=`` and ``height=`` override)."""

VALUE_PADDING_SHARE = 0.06
"""Share of the value span kept free beyond the data on a side that is not anchored at zero."""

RIGHT_MARGIN_SHARE = 0.04
"""Share of the date span left empty beyond the last observation, for the arrow tip."""


def observed_range(
    series: Sequence[TimeSeries], *, include_zero: bool = False
) -> tuple[float, float]:
    """The lowest and highest observed value, widened to include zero on request."""
    values = [value for item in series for value in item.values if value is not None]
    if not values:
        raise ValidationError("cannot draw a series with no observed values")
    low, high = min(values), max(values)
    if include_zero:
        low, high = min(low, 0.0), max(high, 0.0)
    return low, high


def date_marks(series: TimeSeries, *, date_format: str, maximum: int) -> list[AxisMarkLayer]:
    """Marks at evenly spaced observations, one per distinct formatted date."""
    count = len(series.dates)
    if maximum < 2:
        raise ValidationError("a date axis needs at least two marks")
    stride = max(1, math.ceil((count - 1) / (maximum - 1)))
    indices = tuple(range(0, count, stride))
    layers: list[AxisMarkLayer] = []
    seen: set[str] = set()
    for index in indices:
        label = series.dates[index].strftime(date_format)
        if label in seen:
            continue
        seen.add(label)
        layers.append(AxisMarkLayer("x", index, label, id=f"macro.axis.date.{index}", role="axes"))
    return layers


def path_segments(series: TimeSeries) -> tuple[tuple[tuple[float, float], ...], ...]:
    """Observed polyline runs, never connecting across missing values."""
    segments: list[tuple[tuple[float, float], ...]] = []
    current: list[tuple[float, float]] = []
    for index, value in enumerate(series.values):
        if value is None:
            if len(current) >= 2:
                segments.append(tuple(current))
            current = []
        else:
            current.append((float(index), value))
    if len(current) >= 2:
        segments.append(tuple(current))
    return tuple(segments)


def series_layers(specs: Sequence[SeriesSpec]) -> list[Layer]:
    """The paths of every series and a direct label at the last observation of each."""
    layers: list[Layer] = []
    for series, layer_id, role in specs:
        segments = path_segments(series)
        for index, points in enumerate(segments):
            segment_id = layer_id if len(segments) == 1 else f"{layer_id}.segment.{index}"
            layers.append(PathLayer(points, id=segment_id, role=role))
        observed = [(i, v) for i, v in enumerate(series.values) if v is not None]
        if observed:
            index, value = observed[-1]
            layers.append(
                direct_label(
                    (float(index), value), series.name, layer_id=f"{layer_id}.label", role=role
                )
            )
    return layers


def dated_series_canvas(
    specs: Sequence[SeriesSpec],
    *,
    title: str | None,
    include_zero: bool = False,
    x_label: str | None = None,
    y_label: str | None = None,
    date_format: str = "%Y",
    max_date_marks: int = DEFAULT_MARKS + 1,
    value_marks_count: int = DEFAULT_MARKS,
    value_format: str = "{:,g}",
    show_dates: bool = True,
    width: float = SERIES_WIDTH,
    height: float = SERIES_HEIGHT,
    before: Sequence[Layer] = (),
    after: Sequence[Layer] = (),
) -> Canvas:
    """Build a dated line chart from aligned series.

    ``x_label`` and ``y_label`` are drawn as given; ``None`` draws no x title and, for y,
    the unit of the first series; an empty string draws none. Values get rounded marks,
    the vertical range starts at a rounded bound below the data (at zero when
    ``include_zero``), and a dotted zero line is drawn when the range crosses zero.
    """
    if not specs:
        raise ValidationError("at least one series is required")
    reference = specs[0][0]
    for series, _, _ in specs[1:]:
        reference.require_aligned(series, same_unit=False)
    low, high = observed_range([item[0] for item in specs], include_zero=include_zero)
    padding = (high - low) * VALUE_PADDING_SHARE
    anchored_low = include_zero and low >= 0
    anchored_high = include_zero and high <= 0
    y_low, y_high, step = nice_bounds(
        low if anchored_low else low - padding,
        high if anchored_high else high + padding,
        value_marks_count,
    )
    x_range = (0.0, (len(reference.dates) - 1) * (1 + RIGHT_MARGIN_SHARE) or 1.0)
    y_range = (y_low, y_high)
    canvas = new_canvas(canvas_spec(x_range, y_range, width=width, height=height, title=None))
    canvas.extend(before)
    canvas.extend(
        axes_layers(
            x_range,
            y_range,
            x_label=x_label,
            y_label=reference.unit if y_label is None else y_label,
        )
    )
    if y_low < 0 < y_high:
        canvas.add(
            PathLayer(
                ((x_range[0], 0.0), (x_range[1], 0.0)), id="macro.axis.zero", role="macro.guide"
            )
        )
    if show_dates:
        canvas.extend(date_marks(reference, date_format=date_format, maximum=max_date_marks))
    # The lowest mark would collide with the first date at the corner, so a chart with dates
    # leaves it out; its value follows from the step between the marks above.
    marks = tick_values(y_low, y_high, step)
    canvas.extend(
        value_marks(
            "y",
            marks[1:] if show_dates and len(marks) > 2 else marks,
            value_format=value_format,
            id_prefix="macro.axis.value",
        )
    )
    canvas.extend(series_layers(specs))
    canvas.extend(after)
    if title:
        canvas.add(title_layer(x_range, y_range, title, above_label=True))
    return canvas
