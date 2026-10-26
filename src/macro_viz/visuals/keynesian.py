"""Keynesian goods-market figures: consumption function, cross, and multiplier."""

from __future__ import annotations

from collections.abc import Mapping

from mosaickit import BraceLayer, Canvas, Layer, MarkerLayer, PathLayer, TextLayer

from macro_viz.errors import ValidationError
from macro_viz.i18n import Labels
from macro_viz.keynesian.models import (
    DEFAULT_ROUNDS,
    AutonomousShift,
    ConsumptionFunction,
    GoodsMarket,
    KeynesianCross,
)
from macro_viz.open_economy.models import OpenEconomy, OpenEconomyShift
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
    movement,
    movement_label,
    point_name,
    sample,
    shift_arrow,
    theory_canvas,
    trim,
)

SLOPE_RUN_SHARE = 0.2
"""Length of the slope triangle's run as a share of the horizontal axis."""

SLOPE_POSITION = 0.55
"""Where along the horizontal axis the slope triangle starts, as a share of its length."""

SHIFT_ARROW_POSITION = 0.7
"""Where along the horizontal axis the arrow showing a curve's shift stands, as a share of it."""

LABEL_GAP = 4.0
"""Gap in points between a line and the text beside it."""


def consumption_function_canvas(
    function: ConsumptionFunction,
    income_max: float,
    *,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    samples: int = DEFAULT_SAMPLES,
    show_slope: bool = True,
    width: float = THEORY_SIZE,
    height: float = THEORY_SIZE,
) -> Canvas:
    """Draw ``C = c0 + c1 * YD`` with its intercept and, optionally, a slope triangle.

    ``income_max`` is the length of the horizontal axis (disposable income); the vertical axis
    is long enough for the line to end below its top. ``labels`` overrides built-in text by id.
    """
    if income_max <= 0:
        raise ValidationError("income_max must be positive")
    text = Labels(labels)
    y_max = function.consumption(income_max) / HEADROOM
    canvas = theory_canvas(
        income_max,
        y_max,
        labels=text,
        x_label_id="keynesian.axis.disposable_income",
        y_label_id="keynesian.axis.consumption",
        title=title,
        width=width,
        height=height,
    )
    points = trim(sample(function.consumption, 0.0, income_max, samples), income_max, y_max)
    canvas.extend(
        curve(
            points,
            layer_id="macro.keynesian.consumption",
            role="macro.curve.secondary",
            label=text("keynesian.curve.consumption"),
        )
    )
    canvas.add(
        axis_mark(
            "y",
            function.autonomous,
            text("keynesian.mark.intercept"),
            layer_id="macro.keynesian.intercept.mark",
        )
    )
    canvas.add(
        MarkerLayer(
            ((0.0, function.autonomous),),
            id="macro.keynesian.intercept",
            role="macro.point",
            z_index=6,
        )
    )
    if show_slope:
        run = SLOPE_RUN_SHARE * income_max
        x0 = SLOPE_POSITION * income_max
        y0 = function.consumption(x0)
        corner = (x0 + run, y0)
        top = (x0 + run, function.consumption(x0 + run))
        canvas.add(guide((x0, y0), corner, layer_id="macro.keynesian.slope.run"))
        canvas.add(guide(corner, top, layer_id="macro.keynesian.slope.rise"))
        canvas.add(
            TextLayer(
                ((x0 + corner[0]) / 2, y0),
                text("keynesian.mark.slope_run"),
                id="macro.keynesian.slope.run.label",
                role="macro.annotation",
                anchor="top",
                offset=(0, -LABEL_GAP),
            )
        )
        canvas.add(
            TextLayer(
                (corner[0], (y0 + top[1]) / 2),
                text("keynesian.mark.slope_rise"),
                id="macro.keynesian.slope.rise.label",
                role="macro.annotation",
                anchor="left",
                offset=(LABEL_GAP, 0),
            )
        )
    return canvas


def _base_layers(
    model: GoodsMarket,
    x_max: float,
    text: Labels,
    samples: int,
    *,
    demand_id: str = "macro.keynesian.demand",
    demand_label_id: str = "keynesian.curve.demand",
    role: str = "macro.curve.primary",
) -> list[Layer]:
    """The 45-degree production line and the demand curve of ``model``."""
    production = trim([(0.0, 0.0), (x_max, x_max)], x_max, x_max)
    layers: list[Layer] = [
        PathLayer(
            tuple(production),
            id="macro.keynesian.production",
            role="macro.line45",
            clip=False,
            z_index=2,
        ),
        TextLayer(
            production[-1],
            text("keynesian.mark.degrees"),
            id="macro.keynesian.production.label",
            role="macro.annotation",
            anchor="bottom-left",
            offset=(LABEL_GAP, 0),
        ),
    ]
    demand = trim(sample(model.demand, 0.0, x_max, samples), x_max, x_max)
    layers += curve(demand, layer_id=demand_id, role=role, label=text(demand_label_id))
    return layers


def keynesian_cross_canvas(
    model: GoodsMarket,
    *,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    x_max: float | None = None,
    extent: float = EXTENT,
    samples: int = DEFAULT_SAMPLES,
    show_autonomous: bool | None = None,
    width: float = THEORY_SIZE,
    height: float = THEORY_SIZE,
) -> Canvas:
    """Draw the 45-degree production line, the demand curve, and their crossing A.

    ``model`` is a ``KeynesianCross`` (a line) or a ``CurvedDemand``. The axes are square and
    ``x_max`` defaults to ``extent`` times the equilibrium output. The autonomous-spending
    bracket on the vertical axis is drawn for a ``KeynesianCross`` unless
    ``show_autonomous`` says otherwise.
    """
    equilibrium = model.equilibrium()
    limit = x_max if x_max is not None else extent * equilibrium.output
    text = Labels(labels)
    canvas = theory_canvas(
        limit,
        limit,
        labels=text,
        x_label_id="keynesian.axis.income",
        y_label_id="keynesian.axis.demand",
        title=title,
        width=width,
        height=height,
    )
    canvas.extend(_base_layers(model, limit, text, samples))
    point = (equilibrium.output, equilibrium.demand)
    canvas.extend(
        drop_lines(
            point,
            x_label=text("keynesian.mark.output"),
            y_label=text("keynesian.mark.output"),
            layer_id="macro.keynesian.equilibrium.guide",
        )
    )
    canvas.extend(marked_point(point, point_name(0), layer_id="macro.keynesian.equilibrium"))
    drawn = isinstance(model, KeynesianCross) if show_autonomous is None else show_autonomous
    intercept = model.demand(0.0)
    if drawn and intercept > 0:
        canvas.add(
            BraceLayer(
                "y",
                0.0,
                intercept,
                label=text("keynesian.mark.autonomous"),
                side="outside",
                id="macro.keynesian.autonomous",
                role="macro.annotation",
            )
        )
    return canvas


def multiplier_canvas(
    shift: AutonomousShift,
    *,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    rounds: int = DEFAULT_ROUNDS,
    show_path: bool = True,
    x_max: float | None = None,
    extent: float = EXTENT,
    samples: int = DEFAULT_SAMPLES,
    width: float = THEORY_SIZE,
    height: float = THEORY_SIZE,
) -> Canvas:
    """Draw a change in autonomous spending and the multiplier process behind it.

    The old demand line stays heavy; the new one is thin and solid. With ``show_path`` the
    first ``rounds`` rounds are drawn as steps between the new demand line and the 45-degree
    line, from A toward A', named A, B, C, D, E. An arrow beside the lines shows the shift.
    """
    baseline = shift.baseline.equilibrium()
    post = shift.post.equilibrium()
    limit = x_max if x_max is not None else extent * max(baseline.output, post.output)
    text = Labels(labels)
    canvas = theory_canvas(
        limit,
        limit,
        labels=text,
        x_label_id="keynesian.axis.income",
        y_label_id="keynesian.axis.demand",
        title=title,
        width=width,
        height=height,
    )
    canvas.extend(_base_layers(shift.baseline, limit, text, samples))
    shifted = trim(sample(shift.post.demand, 0.0, limit, samples), limit, limit)
    canvas.extend(
        curve(
            shifted,
            layer_id="macro.keynesian.demand.shifted",
            role="macro.curve.primary.shifted",
            label=text("keynesian.curve.demand_shifted"),
        )
    )
    start = (baseline.output, baseline.demand)
    end = (post.output, post.demand)
    canvas.extend(
        drop_lines(
            start,
            x_label=text("keynesian.mark.output"),
            y_label=text("keynesian.mark.output"),
            layer_id="macro.keynesian.equilibrium.guide",
        )
    )
    canvas.extend(
        drop_lines(
            end,
            x_label=text("keynesian.mark.output_shifted"),
            y_label=text("keynesian.mark.output_shifted"),
            layer_id="macro.keynesian.equilibrium.shifted.guide",
        )
    )
    canvas.extend(marked_point(start, point_name(0), layer_id="macro.keynesian.equilibrium"))
    canvas.extend(
        marked_point(
            end,
            point_name(0, prime=1),
            layer_id="macro.keynesian.equilibrium.shifted",
            role="macro.point.shifted",
        )
    )
    arrow_x = SHIFT_ARROW_POSITION * limit
    canvas.extend(
        movement_label(
            (arrow_x, shift.baseline.demand(arrow_x)),
            (arrow_x, shift.post.demand(arrow_x)),
            text("keynesian.mark.shift"),
            layer_id="macro.keynesian.shift",
        )
    )
    if show_path:
        canvas.extend(_path_layers(shift, rounds, text))
    return canvas


def _path_layers(shift: AutonomousShift, rounds: int, text: Labels) -> list[Layer]:
    """Steps of the multiplier process: vertical to the new demand line, horizontal to the 45."""
    layers: list[Layer] = []
    steps = shift.adjustment_path(rounds)
    index = 1
    for step in steps:
        corner = (step.previous_output, step.demand)
        target = (step.output, step.output)
        before = (
            step.previous_output,
            step.previous_output if step.round == 1 else step.previous_output,
        )
        layers.append(
            movement(before, corner, layer_id=f"macro.keynesian.step.{step.round}.demand")
        )
        layers.append(
            movement(corner, target, layer_id=f"macro.keynesian.step.{step.round}.output")
        )
        layers.extend(
            marked_point(corner, point_name(index), layer_id=f"macro.keynesian.step.{step.round}.b")
        )
        layers.extend(
            marked_point(
                target, point_name(index + 1), layer_id=f"macro.keynesian.step.{step.round}.c"
            )
        )
        index += 2
    return layers


def open_goods_canvas(
    subject: OpenEconomy | OpenEconomyShift,
    *,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    show_balanced_trade: bool = True,
    **options: object,
) -> Canvas:
    """Draw the open-economy goods market: the 45-degree line, demand, and equilibrium A.

    Given an ``OpenEconomyShift`` the new demand line is thin and solid with its crossing A'.
    ``show_balanced_trade`` adds a dotted vertical at the output where net exports are zero:
    A to its left means a trade surplus, to its right a trade deficit.
    """
    shift = subject if isinstance(subject, OpenEconomyShift) else None
    model = shift.baseline if shift is not None else subject
    assert isinstance(model, OpenEconomy)
    if shift is None:
        canvas = keynesian_cross_canvas(model, title=title, labels=labels, **options)  # type: ignore[arg-type]
    else:
        canvas = _open_shift(shift, title, labels, options)
    if show_balanced_trade and model.import_propensity > 0:
        limit = canvas.spec.x_max
        balanced = model.balanced_trade_output()
        if balanced < limit * HEADROOM:
            text = Labels(labels)
            canvas.add(guide((balanced, 0.0), (balanced, balanced), layer_id="macro.open.balanced"))
            canvas.add(
                axis_mark(
                    "x", balanced, text("open.mark.balanced"), layer_id="macro.open.balanced.mark"
                )
            )
    return canvas


def _open_shift(
    shift: OpenEconomyShift,
    title: str | None,
    labels: Mapping[str, str] | None,
    options: Mapping[str, object],
) -> Canvas:
    baseline, post = shift.baseline, shift.post
    limit = options.get("x_max")
    extent = float(options.get("extent", EXTENT))  # type: ignore[arg-type]
    samples = int(options.get("samples", DEFAULT_SAMPLES))  # type: ignore[call-overload]
    right = (
        float(limit)  # type: ignore[arg-type]
        if limit is not None
        else extent * max(baseline.equilibrium().output, post.equilibrium().output)
    )
    text = Labels(labels)
    canvas = theory_canvas(
        right,
        right,
        labels=text,
        x_label_id="keynesian.axis.income",
        y_label_id="keynesian.axis.demand",
        title=title,
    )
    canvas.extend(_base_layers(baseline, right, text, samples))
    canvas.extend(
        curve(
            trim(sample(post.demand, 0.0, right, samples), right, right),
            layer_id="macro.keynesian.demand.shifted",
            role="macro.curve.primary.shifted",
            label=text("keynesian.curve.demand_shifted"),
        )
    )
    for index, (m, name, role) in enumerate(
        (
            (baseline, "macro.keynesian.equilibrium", "macro.point"),
            (post, "macro.keynesian.equilibrium.shifted", "macro.point.shifted"),
        )
    ):
        e = m.equilibrium()
        point = (e.output, e.demand)
        canvas.extend(
            drop_lines(
                point,
                x_label=text(
                    "keynesian.mark.output" if index == 0 else "keynesian.mark.output_shifted"
                ),
                y_label=text(
                    "keynesian.mark.output" if index == 0 else "keynesian.mark.output_shifted"
                ),
                layer_id=f"{name}.guide",
            )
        )
        canvas.extend(marked_point(point, point_name(0, prime=index), layer_id=name, role=role))
    old = baseline.equilibrium()
    canvas.add(
        shift_arrow(
            (old.output, old.demand),
            (old.output, post.demand(old.output)),
            layer_id="macro.keynesian.shift",
        )
    )
    return canvas
