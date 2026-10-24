"""Shared renderer-neutral layer construction for dated series."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from mosaickit import AxisMarkLayer, AxisSpec, Canvas, CanvasSpec, PathLayer, TextLayer, build_axes
from mosaickit.styles.nudge import Nudge

from macro_viz.config import active_config
from macro_viz.errors import ValidationError
from macro_viz.series import TimeSeries

SeriesSpec = tuple[TimeSeries, str, str, str]


def new_canvas(spec: CanvasSpec) -> Canvas:
    """Create a canvas with the active macro-viz MosaicKit configuration."""
    return Canvas(spec, config=active_config().mosaickit_config())


def observed_range(
    series: Iterable[TimeSeries], *, include_zero: bool = False
) -> tuple[float, float]:
    values = [value for item in series for value in item.values if value is not None]
    if not values:
        raise ValidationError("cannot draw a series with no observed values")
    low, high = min(values), max(values)
    if include_zero:
        low, high = min(low, 0.0), max(high, 0.0)
    span = high - low
    padding = span * 0.08 if span else max(abs(high) * 0.08, 1.0)
    return (low - padding, high + padding)


def date_mark_layers(series: TimeSeries, *, maximum: int = 5) -> list[AxisMarkLayer]:
    count = len(series.dates)
    if count <= maximum:
        indices = tuple(range(count))
    else:
        indices = tuple(round(index * (count - 1) / (maximum - 1)) for index in range(maximum))
    return [
        AxisMarkLayer(
            "x",
            index,
            series.dates[index].isoformat(),
            id=f"macro.axis.date.{index}",
            role="axes",
        )
        for index in indices
    ]


def value_mark_layers(y_range: tuple[float, float], *, count: int = 5) -> list[AxisMarkLayer]:
    """Evenly spaced value labels for a continuous vertical axis."""
    low, high = y_range
    values = tuple(low + index * (high - low) / (count - 1) for index in range(count))
    return [
        AxisMarkLayer(
            "y",
            value,
            f"{value:,.4g}",
            id=f"macro.axis.value.{index}",
            role="axes",
        )
        for index, value in enumerate(values)
    ]


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


def series_layers(specs: Sequence[SeriesSpec]) -> list[PathLayer | TextLayer]:
    layers: list[PathLayer | TextLayer] = []
    observed_by_id: dict[str, list[tuple[int, float]]] = {}
    for series, layer_id, _, _ in specs:
        observed_by_id[layer_id] = [
            (index, value) for index, value in enumerate(series.values) if value is not None
        ]
    final_values = {
        layer_id: observed[-1][1] for layer_id, observed in observed_by_id.items() if observed
    }
    unique_final_values = set(final_values.values())
    for series, layer_id, role, label in specs:
        segments = path_segments(series)
        for index, points in enumerate(segments):
            segment_id = layer_id if len(segments) == 1 else f"{layer_id}.segment.{index}"
            layers.append(PathLayer(points, id=segment_id, role=role, legend=label))
        observed = observed_by_id[layer_id]
        if observed:
            index, value = observed[-1]
            nudge = None
            if len(unique_final_values) > 1:
                if value == max(unique_final_values):
                    nudge = Nudge(dy=6)
                elif value == min(unique_final_values):
                    nudge = Nudge(dy=-6)
            layers.append(
                TextLayer(
                    (index, value),
                    label,
                    id=f"{layer_id}.label",
                    role=role,
                    anchor="left",
                    offset=(5, 0),
                    nudge=nudge,
                )
            )
    return layers


def dated_series_canvas(
    specs: Sequence[SeriesSpec],
    *,
    title: str | None,
    include_zero: bool = False,
    before: Sequence = (),  # type: ignore[type-arg]
    after: Sequence = (),  # type: ignore[type-arg]
) -> Canvas:
    """Build a dated line chart from aligned series specifications."""
    if not specs:
        raise ValidationError("at least one series is required")
    reference = specs[0][0]
    for series, _, _, _ in specs[1:]:
        reference.require_aligned(series, same_unit=False)
    y_range = observed_range((item[0] for item in specs), include_zero=include_zero)
    x_range = (0.0, float(max(len(reference.dates) - 1, 1)))
    spec = CanvasSpec(
        x_range=x_range,
        y_range=y_range,
        width=7.0,
        height=4.5,
        x_label="Date",
        y_label=reference.unit,
        title=title,
    )
    canvas = new_canvas(spec)
    canvas.extend(before)
    canvas.extend(build_axes(AxisSpec(x_range), AxisSpec(y_range)))
    canvas.extend(date_mark_layers(reference))
    canvas.extend(value_mark_layers(y_range))
    canvas.extend(series_layers(specs))
    canvas.extend(after)
    return canvas
