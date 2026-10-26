"""Aggregate supply and aggregate demand figures."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from mosaickit import Canvas, TextLayer

from macro_viz.adas.models import AggregateDemand, AggregateSupply
from macro_viz.errors import ValidationError
from macro_viz.i18n import Labels
from macro_viz.visuals._theory import (
    DEFAULT_SAMPLES,
    EXTENT,
    THEORY_SIZE,
    axis_mark,
    curve,
    drop_lines,
    guide,
    marked_point,
    point_name,
    shift_arrow,
    theory_canvas,
)
from macro_viz.visuals.adas._curves import demand_curve, supply_curve
from macro_viz.visuals.adas._preset import LABEL_GAP


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
    right = x_max if x_max is not None else extent * supply.effective_natural_output
    top = (
        y_max
        if y_max is not None
        else extent * max(c.price(c.effective_natural_output) for c in curves)
    )
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
    anchor = (supply.effective_natural_output, supply.price(supply.effective_natural_output))
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
        moved = (shifted.effective_natural_output, shifted.price(shifted.effective_natural_output))
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
            shift_arrow(
                anchor,
                (anchor[0], shifted.price(anchor[0])),
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
    vertical axis) an arrow runs from ``AD`` to each shifted curve and, when given,
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
        canvas.add(shift_arrow(start, end, layer_id=f"macro.adas.shift{suffix}"))
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
