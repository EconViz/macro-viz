"""Aggregate supply and aggregate demand figures."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from mosaickit import AxisNoteLayer, Canvas, Layer, TextLayer

from macro_viz.adas.analysis import ASADShift, Shock
from macro_viz.adas.models import AggregateDemand, AggregateSupply, ASADModel
from macro_viz.errors import ValidationError
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
    movement,
    point_name,
    sample,
    theory_canvas,
    trim,
)

SHIFT_ARROW_SHARE = 0.55
"""Height of the arrow showing a curve's shift, as a share of the vertical axis."""

AMBIGUOUS_SPAN_SHARE = 0.08
"""Length of each arrow of an ambiguous shift, as a share of the horizontal axis."""

LABEL_GAP = 4.0
"""Gap in points between an arrow and the text beside it."""


def supply_curve(
    supply: AggregateSupply, x_max: float, y_max: float, samples: int
) -> list[tuple[float, float]]:
    """The aggregate supply curve inside the plot."""
    return trim(sample(supply.price, 0.0, x_max, samples), x_max, y_max)


def demand_curve(
    demand: AggregateDemand, x_max: float, y_max: float, samples: int
) -> list[tuple[float, float]]:
    """The aggregate demand curve from the top of the plot to the right edge."""
    top = HEADROOM * y_max
    start = demand.autonomous + demand.multiplier * demand.money / top
    stop = HEADROOM * x_max
    if start >= stop:
        raise ValidationError("the demand curve does not enter the plot; widen the axes")
    return sample(demand.price, start, stop, samples)


def _scale(
    models: Sequence[ASADModel], x_max: float | None, y_max: float | None, extent: float
) -> tuple[float, float]:
    outputs, prices = [], []
    for model in models:
        equilibrium = model.equilibrium()
        outputs += [equilibrium.output, equilibrium.natural_output]
        prices += [equilibrium.price, equilibrium.expected_price]
    return (
        x_max if x_max is not None else extent * max(outputs),
        y_max if y_max is not None else extent * max(prices),
    )


def aggregate_supply_canvas(
    supply: AggregateSupply,
    *,
    shifted: AggregateSupply | None = None,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    x_max: float | None = None,
    y_max: float | None = None,
    extent: float = EXTENT,
    samples: int = DEFAULT_SAMPLES,
    width: float = THEORY_SIZE,
    height: float = THEORY_SIZE,
) -> Canvas:
    """Draw aggregate supply through its anchor ``A = (Yn, Pe)`` where the price is expected.

    With ``shifted`` (a supply with another expected price level) the new curve is thin and
    dashed, runs through ``A'`` at the same natural output, and an arrow shows the shift.
    """
    text = Labels(labels)
    curves = [supply] + ([shifted] if shifted is not None else [])
    right = x_max if x_max is not None else extent * supply.natural_output
    top = y_max if y_max is not None else extent * max(c.price(c.natural_output) for c in curves)
    canvas = theory_canvas(
        right,
        top,
        labels=text,
        x_label_id="adas.axis.output",
        y_label_id="adas.axis.price",
        title=title,
        width=width,
        height=height,
    )
    canvas.extend(
        curve(
            supply_curve(supply, right, top, samples),
            layer_id="macro.adas.supply",
            role="macro.curve.secondary",
            label=text("adas.curve.supply"),
        )
    )
    anchor = (supply.natural_output, supply.price(supply.natural_output))
    canvas.extend(
        drop_lines(
            anchor,
            x_label=text("adas.mark.natural_output"),
            y_label=text("adas.mark.anchor_price"),
            layer_id="macro.adas.anchor.guide",
        )
    )
    canvas.extend(marked_point(anchor, point_name(0), layer_id="macro.adas.anchor"))
    if shifted is not None:
        canvas.extend(
            curve(
                supply_curve(shifted, right, top, samples),
                layer_id="macro.adas.supply.shifted",
                role="macro.curve.secondary.shifted",
                label=text("adas.curve.supply_shifted"),
            )
        )
        moved = (shifted.natural_output, shifted.price(shifted.natural_output))
        canvas.extend(
            drop_lines(
                moved,
                x_label=None,
                y_label=text("adas.mark.anchor_price_shifted"),
                layer_id="macro.adas.anchor.shifted.guide",
            )
        )
        canvas.extend(
            marked_point(
                moved,
                point_name(0, prime=1),
                layer_id="macro.adas.anchor.shifted",
                role="macro.point.shifted",
            )
        )
        canvas.add(
            movement(
                (SHIFT_ARROW_SHARE * right, supply.price(SHIFT_ARROW_SHARE * right)),
                (SHIFT_ARROW_SHARE * right, shifted.price(SHIFT_ARROW_SHARE * right)),
                layer_id="macro.adas.shift",
            )
        )
    return canvas


def aggregate_demand_canvas(
    demand: AggregateDemand,
    shifts: Sequence[AggregateDemand] = (),
    *,
    price: float | None = None,
    captions: Sequence[str] = (),
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    x_max: float,
    y_max: float,
    samples: int = DEFAULT_SAMPLES,
    width: float = THEORY_SIZE,
    height: float = THEORY_SIZE,
) -> Canvas:
    """Draw aggregate demand and its shifted positions at a given price level.

    The curves are named ``AD``, ``AD'``, ``AD''``; at ``price`` (default: the middle of the
    vertical axis) a dashed arrow runs from ``AD`` to each shifted curve and, when given,
    ``captions[k]`` names what moved curve ``k``. ``x_max`` and ``y_max`` fix the axes.
    """
    text = Labels(labels)
    canvas = theory_canvas(
        x_max,
        y_max,
        labels=text,
        x_label_id="adas.axis.output",
        y_label_id="adas.axis.price",
        title=title,
        width=width,
        height=height,
    )
    level = price if price is not None else y_max / 2
    names = ("adas.curve.demand_shifted", "adas.curve.demand_shifted_again")
    if len(shifts) > len(names):
        raise ValidationError(f"at most {len(names)} shifted demand curves can be drawn")
    canvas.extend(
        curve(
            demand_curve(demand, x_max, y_max, samples),
            layer_id="macro.adas.demand",
            role="macro.curve.primary",
            label=text("adas.curve.demand"),
        )
    )
    for index, shifted in enumerate(shifts):
        suffix = "" if index == 0 else f".{index}"
        canvas.extend(
            curve(
                demand_curve(shifted, x_max, y_max, samples),
                layer_id=f"macro.adas.demand.shifted{suffix}",
                role="macro.curve.primary.shifted",
                label=text(names[index]),
            )
        )
        start, end = (demand.output(level), level), (shifted.output(level), level)
        canvas.add(movement(start, end, layer_id=f"macro.adas.shift{suffix}"))
        if index < len(captions):
            canvas.add(
                TextLayer(
                    end,
                    captions[index],
                    id=f"macro.adas.shift{suffix}.caption",
                    role="macro.annotation",
                    anchor="bottom-left" if end[0] > start[0] else "bottom-right",
                    offset=(LABEL_GAP, LABEL_GAP) if end[0] > start[0] else (-LABEL_GAP, LABEL_GAP),
                )
            )
    canvas.add(axis_mark("y", level, text("adas.mark.price"), layer_id="macro.adas.price.mark"))
    canvas.add(
        guide((0.0, level), (demand.output(level), level), layer_id="macro.adas.price.guide")
    )
    return canvas


def adas_canvas(
    subject: ASADModel | ASADShift,
    *,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    x_max: float | None = None,
    y_max: float | None = None,
    extent: float = EXTENT,
    samples: int = DEFAULT_SAMPLES,
    show_natural_output: bool = True,
    productivity: float | None = None,
    ambiguous_demand: bool = False,
    width: float = THEORY_SIZE,
    height: float = THEORY_SIZE,
) -> Canvas:
    """Draw aggregate supply and demand, their crossing A, and optionally a shock.

    ``show_natural_output`` adds the dashed vertical at ``Yn``, the point ``B = (Yn, Pe)`` on AS,
    and the mark ``Pe``. Given an ``ASADShift`` the moved curve is thin and dashed and the new
    crossing is A'. ``productivity`` (the level ``A`` of ``N = Y / A``) names the employment
    that goes with equilibrium output below the axis. ``ambiguous_demand`` marks the unknown
    direction of a demand shift with two arrows and question marks.
    """
    shift = subject if isinstance(subject, ASADShift) else None
    model = shift.baseline if shift is not None else subject
    assert isinstance(model, ASADModel)
    models = [model] + ([shift.post] if shift is not None else [])
    right, top = _scale(models, x_max, y_max, extent)
    text = Labels(labels)
    canvas = theory_canvas(
        right,
        top,
        labels=text,
        x_label_id="adas.axis.output",
        y_label_id="adas.axis.price",
        title=title,
        width=width,
        height=height,
    )
    equilibrium = model.equilibrium()
    canvas.extend(
        curve(
            supply_curve(model.supply, right, top, samples),
            layer_id="macro.adas.supply",
            role="macro.curve.secondary",
            label=text("adas.curve.supply"),
        )
    )
    canvas.extend(
        curve(
            demand_curve(model.demand, right, top, samples),
            layer_id="macro.adas.demand",
            role="macro.curve.primary",
            label=text("adas.curve.demand"),
        )
    )
    if show_natural_output:
        canvas.extend(_natural_layers(model, right, top, text))
    point = (equilibrium.output, equilibrium.price)
    canvas.extend(
        drop_lines(
            point,
            x_label=text("adas.mark.output"),
            y_label=text("adas.mark.price"),
            layer_id="macro.adas.equilibrium.guide",
        )
    )
    canvas.extend(marked_point(point, point_name(0), layer_id="macro.adas.equilibrium"))
    if productivity is not None:
        canvas.add(
            AxisNoteLayer(
                "x",
                equilibrium.output,
                text("adas.note.employment"),
                id="macro.adas.employment",
                role="macro.annotation",
            )
        )
    if shift is not None:
        canvas.extend(_shift_layers(shift, right, top, samples, text, ambiguous_demand))
    return canvas


def _natural_layers(model: ASADModel, right: float, top: float, text: Labels) -> list[Layer]:
    equilibrium = model.equilibrium()
    natural, expected = equilibrium.natural_output, equilibrium.expected_price
    anchor = (natural, model.supply.price(natural))
    layers: list[Layer] = [
        guide((natural, 0.0), (natural, HEADROOM * top), layer_id="macro.adas.natural"),
        axis_mark(
            "x", natural, text("adas.mark.natural_output"), layer_id="macro.adas.natural.mark"
        ),
    ]
    if abs(anchor[1] - expected) < expected * 1e-9:
        layers += drop_lines(
            anchor,
            x_label=None,
            y_label=text("adas.mark.expected_price"),
            layer_id="macro.adas.expected",
        )
        layers += marked_point(anchor, point_name(1), layer_id="macro.adas.anchor")
    return layers


def _shift_layers(
    shift: ASADShift,
    right: float,
    top: float,
    samples: int,
    text: Labels,
    ambiguous: bool,
) -> list[Layer]:
    layers: list[Layer] = []
    post = shift.post
    if shift.shock is Shock.SUPPLY:
        layers += curve(
            supply_curve(post.supply, right, top, samples),
            layer_id="macro.adas.supply.shifted",
            role="macro.curve.secondary.shifted",
            label=text("adas.curve.supply_shifted"),
        )
        x = SHIFT_ARROW_SHARE * right
        layers.append(
            movement(
                (x, shift.baseline.supply.price(x)),
                (x, post.supply.price(x)),
                layer_id="macro.adas.shift",
            )
        )
    else:
        layers += curve(
            demand_curve(post.demand, right, top, samples),
            layer_id="macro.adas.demand.shifted",
            role="macro.curve.primary.shifted",
            label=text("adas.curve.demand_shifted"),
        )
        level = SHIFT_ARROW_SHARE * top
        layers.append(
            movement(
                (shift.baseline.demand.output(level), level),
                (post.demand.output(level), level),
                layer_id="macro.adas.shift",
            )
        )
    if ambiguous:
        layers += _ambiguous_layers(shift, right, top, text)
    end = post.equilibrium()
    point = (end.output, end.price)
    layers += drop_lines(
        point,
        x_label=text("adas.mark.output_shifted"),
        y_label=text("adas.mark.price_shifted"),
        layer_id="macro.adas.equilibrium.shifted.guide",
    )
    layers += marked_point(
        point,
        point_name(0, prime=1),
        layer_id="macro.adas.equilibrium.shifted",
        role="macro.point.shifted",
    )
    return layers


def _ambiguous_layers(shift: ASADShift, right: float, top: float, text: Labels) -> list[Layer]:
    """Two arrows from the demand curve, left and right, each marked with a question mark."""
    level = SHIFT_ARROW_SHARE * top
    start = shift.baseline.demand.output(level)
    span = AMBIGUOUS_SPAN_SHARE * right
    layers: list[Layer] = []
    for name, sign in (("left", -1), ("right", 1)):
        end = (start + sign * span, level)
        layers.append(movement((start, level), end, layer_id=f"macro.adas.ambiguous.{name}"))
        layers.append(
            TextLayer(
                end,
                text("adas.mark.ambiguous"),
                id=f"macro.adas.ambiguous.{name}.label",
                role="macro.annotation",
                anchor="bottom",
                offset=(0, LABEL_GAP),
            )
        )
    return layers
