"""Time paths of the Solow model."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from mosaickit import Canvas

from macro_viz.core.i18n import Labels
from macro_viz.growth.models import SolowPath
from macro_viz.growth.visuals._preset import PATH_HEADROOM
from macro_viz.visuals._theory import (
    HEADROOM,
    THEORY_SIZE,
    axis_mark,
    curve,
    guide,
    theory_canvas,
    trim,
)


def _path_axes(
    path: SolowPath,
    values: Sequence[float],
    *,
    y_label_id: str,
    title: str | None,
    labels: Mapping[str, str] | None,
    width: float,
    height: float,
) -> tuple[Canvas, Labels, float, float]:
    """A canvas for a time path: time on the horizontal axis, room above the highest value."""
    text = Labels(labels)
    right = float(path.periods - 1)
    low, high = min(values), max(values)
    top = high + PATH_HEADROOM * (high - low if high > low else abs(high) or 1.0)
    canvas = theory_canvas(
        right,
        top,
        labels=text,
        x_label_id="solow.axis.time",
        y_label_id=y_label_id,
        title=title,
        width=width,
        height=height,
    )
    return canvas, text, right, top


def solow_level_path_canvas(
    path: SolowPath,
    *,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    width: float = THEORY_SIZE,
    height: float = THEORY_SIZE,
) -> Canvas:
    """Draw output per worker over time: flat, then rising to the new steady-state level.

    The old and new levels are marked on the output axis with dashed guides.
    """
    values = path.output
    canvas, text, right, _ = _path_axes(
        path,
        values,
        y_label_id="solow.axis.output",
        title=title,
        labels=labels,
        width=width,
        height=height,
    )
    canvas.extend(
        curve(
            tuple((float(t), v) for t, v in enumerate(values)),
            layer_id="macro.growth.path.level",
            role="macro.curve.primary",
        )
    )
    first, last = values[0], values[-1]
    canvas.add(
        axis_mark("y", first, text("solow.mark.output"), layer_id="macro.growth.level.old.mark")
    )
    canvas.add(
        axis_mark(
            "y", last, text("solow.mark.output_shifted"), layer_id="macro.growth.level.new.mark"
        )
    )
    canvas.add(guide((0.0, first), (right, first), layer_id="macro.growth.level.old"))
    canvas.add(guide((0.0, last), (right, last), layer_id="macro.growth.level.new"))
    return canvas


def solow_log_path_canvas(
    path: SolowPath,
    *,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    width: float = THEORY_SIZE,
    height: float = THEORY_SIZE,
) -> Canvas:
    """Draw ``log`` output over time with the trend lines before and after the change.

    With technological progress both trends have the slope ``log(1 + gA)``; the transition curve
    joins them. The vertical axis is a log scale shifted to start at zero.
    """
    logs = path.log_output
    floor = min(logs)
    values = tuple(v - floor for v in logs)
    canvas, text, right, top = _path_axes(
        path,
        values,
        y_label_id="solow.axis.log_output",
        title=title,
        labels=labels,
        width=width,
        height=height,
    )
    growth = math.log1p(path.post.tech_growth)
    canvas.extend(
        curve(
            tuple((float(t), v) for t, v in enumerate(values)),
            layer_id="macro.growth.path.log",
            role="macro.curve.primary",
        )
    )
    old = values[0]
    new = values[-1]
    old_trend = tuple((float(t), old + growth * t) for t in range(path.periods))
    new_trend = tuple(
        (float(t), new + growth * (t - (path.periods - 1))) for t in range(path.periods)
    )
    for name, points in (("old", old_trend), ("new", new_trend)):
        canvas.extend(
            curve(
                trim(points, right, top),
                layer_id=f"macro.growth.trend.{name}",
                role="macro.curve.secondary.shifted",
                label=text("solow.mark.trend") if name == "new" else None,
            )
        )
    return canvas


def solow_growth_rate_canvas(
    path: SolowPath,
    *,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    width: float = THEORY_SIZE,
    height: float = THEORY_SIZE,
) -> Canvas:
    """Draw the growth rate of output per worker: a jump at the change, then decay to its trend."""
    rates = path.growth_rates
    values = tuple(max(r, 0.0) for r in rates)
    canvas = theory_canvas(
        float(len(rates) - 1),
        max(values) / HEADROOM,
        labels=Labels(labels),
        x_label_id="solow.axis.time",
        y_label_id="solow.axis.growth",
        title=title,
        width=width,
        height=height,
    )
    canvas.extend(
        curve(
            tuple((float(t), v) for t, v in enumerate(values)),
            layer_id="macro.growth.path.rate",
            role="macro.curve.primary",
        )
    )
    return canvas
