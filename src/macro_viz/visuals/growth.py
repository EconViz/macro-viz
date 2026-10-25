"""Solow growth figures: production function, steady state, golden rule, and time paths."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from mosaickit import ArrowLayer, Canvas, Layer

from macro_viz.errors import ValidationError
from macro_viz.growth.analysis import SteadyStateShift
from macro_viz.growth.models import Solow, SolowPath
from macro_viz.i18n import Labels
from macro_viz.visuals._theory import (
    DEFAULT_SAMPLES,
    EXTENT,
    HEADROOM,
    THEORY_SIZE,
    axis_mark,
    curve,
    drop_lines,
    guide,
    marked_point,
    point_name,
    sample,
    shift_arrow,
    theory_canvas,
    trim,
)

CONVERGENCE_HEIGHT_SHARE = 0.03
"""Height of the convergence arrows above the capital axis, as a share of the output axis."""

CONVERGENCE_SPAN_SHARE = 0.12
"""Length of each convergence arrow, as a share of the capital axis."""

SOLOW_EXTENT = 2.4
"""Default length of the capital axis in the Solow diagram, as a multiple of the steady state,
so saving and required investment end well apart and the steady state sits left of centre."""

PATH_HEADROOM = 0.3
"""Room above the highest value of a time path, as a share of its range."""

GOLDEN_SAMPLES_FLOOR = 0.02
"""The saving-rate axis of the golden-rule figure starts this far from zero and stops this far from
one: consumption is undefined at the ends."""


def _ids(effective: bool) -> str:
    return "solow.effective." if effective else "solow."


def _limits(
    models: Sequence[Solow], k_max: float | None, y_max: float | None, extent: float
) -> tuple[float, float]:
    right = k_max if k_max is not None else extent * max(m.steady_state() for m in models)
    top = y_max if y_max is not None else max(m.output(right) for m in models) / HEADROOM
    return right, top


def production_function_canvas(
    model: Solow,
    *,
    shifted: Solow | None = None,
    points: Sequence[float] = (),
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    effective: bool = False,
    k_max: float | None = None,
    y_max: float | None = None,
    extent: float = EXTENT,
    samples: int = DEFAULT_SAMPLES,
    width: float = THEORY_SIZE,
    height: float = THEORY_SIZE,
) -> Canvas:
    """Draw the concave production function with points at the given capital levels.

    Each capital level in ``points`` gets a dot named A, B, ... with guides to both axes; with
    ``shifted`` (better technology, another function) the new curve is thin and solid and a
    curved arrow shows the upward shift.
    """
    prefix, text = _ids(effective), Labels(labels)
    models = [model] + ([shifted] if shifted is not None else [])
    right, top = _limits(models, k_max, y_max, extent)
    if shifted is not None and y_max is None:
        top = max(m.output(right) for m in models) / HEADROOM
    canvas = theory_canvas(
        right,
        top,
        labels=text,
        x_label_id=f"{prefix}axis.capital",
        y_label_id=f"{prefix}axis.output",
        title=title,
        width=width,
        height=height,
    )
    canvas.extend(
        curve(
            trim(sample(model.output, 0.0, right, samples), right, top),
            layer_id="macro.growth.production",
            role="macro.curve.primary",
            label=text(f"{prefix}curve.production"),
        )
    )
    for index, capital in enumerate(points):
        point = (capital, model.output(capital))
        canvas.extend(
            drop_lines(
                point,
                x_label=None,
                y_label=None,
                layer_id=f"macro.growth.point.{index}.guide",
            )
        )
        canvas.extend(
            marked_point(point, point_name(index), layer_id=f"macro.growth.point.{index}")
        )
    if shifted is not None:
        canvas.extend(
            curve(
                trim(sample(shifted.output, 0.0, right, samples), right, top),
                layer_id="macro.growth.production.shifted",
                role="macro.curve.primary.shifted",
                label=text(f"{prefix}curve.production_shifted"),
            )
        )
        x = points[0] if points else 0.5 * right
        canvas.add(
            shift_arrow((x, model.output(x)), (x, shifted.output(x)), layer_id="macro.growth.shift")
        )
    return canvas


def solow_canvas(
    subject: Solow | SteadyStateShift,
    *,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    effective: bool = False,
    show_production: bool = True,
    show_convergence: bool = True,
    k_max: float | None = None,
    y_max: float | None = None,
    extent: float = SOLOW_EXTENT,
    samples: int = DEFAULT_SAMPLES,
    width: float = THEORY_SIZE,
    height: float = THEORY_SIZE,
) -> Canvas:
    """Draw output, saving ``s f(k)``, and required investment, with the steady state A.

    Given a ``SteadyStateShift`` (a change of the saving rate, population or technology growth)
    the changed curve is thin and solid, the new steady state is A', and a straight arrow shows
    the shift. Arrows along the capital axis point toward each steady state.
    """
    shift = subject if isinstance(subject, SteadyStateShift) else None
    model = shift.baseline if shift is not None else subject
    assert isinstance(model, Solow)
    models = [model] + ([shift.post] if shift is not None else [])
    right, top = _limits(models, k_max, y_max, extent)
    prefix, text = _ids(effective), Labels(labels)
    canvas = theory_canvas(
        right,
        top,
        labels=text,
        x_label_id=f"{prefix}axis.capital",
        y_label_id=f"{prefix}axis.output",
        title=title,
        width=width,
        height=height,
    )
    if show_production:
        canvas.extend(
            curve(
                trim(sample(model.output, 0.0, right, samples), right, top),
                layer_id="macro.growth.production",
                role="macro.curve.primary",
                label=text(f"{prefix}curve.production"),
            )
        )
    canvas.extend(
        curve(
            trim(sample(model.investment, 0.0, right, samples), right, top),
            layer_id="macro.growth.investment",
            role="macro.curve.secondary",
            label=text(f"{prefix}curve.investment"),
        )
    )
    canvas.extend(
        curve(
            trim(sample(model.required_investment, 0.0, right, samples), right, top),
            layer_id="macro.growth.required",
            role="macro.curve.secondary",
            label=text(f"{prefix}curve.required"),
        )
    )
    steady = model.steady_state()
    point = (steady, model.investment(steady))
    canvas.extend(
        drop_lines(
            point,
            x_label=text(f"{prefix}mark.capital"),
            y_label=None,
            layer_id="macro.growth.steady.guide",
        )
    )
    canvas.extend(marked_point(point, point_name(0), layer_id="macro.growth.steady"))
    if show_convergence:
        canvas.extend(_convergence(steady, right, top, "macro.growth.convergence"))
    if shift is not None:
        canvas.extend(_shift_layers(shift, right, top, samples, text, prefix, show_convergence))
    return canvas


def _convergence(steady: float, right: float, top: float, layer_id: str) -> list[Layer]:
    """Two arrows along the capital axis, one from each side, pointing at ``steady``."""
    height = CONVERGENCE_HEIGHT_SHARE * top
    span = CONVERGENCE_SPAN_SHARE * right
    return [
        ArrowLayer(
            (steady - 2 * span, height),
            (steady - 0.25 * span, height),
            id=f"{layer_id}.left",
            role="macro.movement",
            z_index=5,
        ),
        ArrowLayer(
            (steady + 2 * span, height),
            (steady + 0.25 * span, height),
            id=f"{layer_id}.right",
            role="macro.movement",
            z_index=5,
        ),
    ]


def _shift_layers(
    shift: SteadyStateShift,
    right: float,
    top: float,
    samples: int,
    text: Labels,
    prefix: str,
    convergence: bool,
) -> list[Layer]:
    post, base = shift.post, shift.baseline
    layers: list[Layer] = []
    x = base.steady_state()
    if post.saving != base.saving:
        layers += curve(
            trim(sample(post.investment, 0.0, right, samples), right, top),
            layer_id="macro.growth.investment.shifted",
            role="macro.curve.secondary.shifted",
            label=text(f"{prefix}curve.investment_shifted"),
        )
        layers.append(
            shift_arrow(
                (x, base.investment(x)), (x, post.investment(x)), layer_id="macro.growth.shift"
            )
        )
    else:
        layers += curve(
            trim(sample(post.required_investment, 0.0, right, samples), right, top),
            layer_id="macro.growth.required.shifted",
            role="macro.curve.secondary.shifted",
            label=text(f"{prefix}curve.required_shifted"),
        )
        layers.append(
            shift_arrow(
                (x, base.required_investment(x)),
                (x, post.required_investment(x)),
                layer_id="macro.growth.shift",
            )
        )
    steady = post.steady_state()
    point = (steady, post.investment(steady))
    layers += drop_lines(
        point,
        x_label=text(f"{prefix}mark.capital_shifted"),
        y_label=None,
        layer_id="macro.growth.steady.shifted.guide",
    )
    layers += marked_point(
        point,
        point_name(0, prime=1),
        layer_id="macro.growth.steady.shifted",
        role="macro.point.shifted",
    )
    return layers


def golden_rule_canvas(
    model: Solow,
    *,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    effective: bool = False,
    samples: int = DEFAULT_SAMPLES,
    width: float = THEORY_SIZE,
    height: float = THEORY_SIZE,
) -> Canvas:
    """Draw steady-state consumption per worker against the saving rate, with its maximum.

    The hump peaks at the golden-rule saving rate ``s_G``, marked on the saving axis.
    """
    prefix, text = _ids(effective), Labels(labels)
    golden = model.golden_rule_saving()
    if not 0 < golden < 1:
        raise ValidationError("the golden-rule saving rate must lie between 0 and 1")
    points = sample(model.consumption_at, GOLDEN_SAMPLES_FLOOR, 1 - GOLDEN_SAMPLES_FLOOR, samples)
    peak = model.consumption_at(golden)
    top = peak / HEADROOM
    canvas = theory_canvas(
        1.0,
        top,
        labels=text,
        x_label_id=f"{prefix}axis.saving",
        y_label_id=f"{prefix}axis.consumption",
        title=title,
        width=width,
        height=height,
    )
    canvas.extend(
        curve(
            points,
            layer_id="macro.growth.consumption",
            role="macro.curve.primary",
            label=text(f"{prefix}curve.consumption"),
        )
    )
    canvas.extend(
        drop_lines(
            (golden, peak),
            x_label=text(f"{prefix}mark.golden"),
            y_label=None,
            layer_id="macro.growth.golden.guide",
        )
    )
    canvas.extend(marked_point((golden, peak), point_name(0), layer_id="macro.growth.golden"))
    return canvas


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
