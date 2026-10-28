"""The AD-AS figure of an adjustment path."""

from __future__ import annotations

from collections.abc import Mapping

from mosaickit import Canvas

from macro_viz.adas.adjustment import AdjustmentPath
from macro_viz.adas.visuals._curves import demand_curve, supply_curve
from macro_viz.adas.visuals._preset import MARKED_OUTPUTS, SAME_OUTPUT
from macro_viz.core.i18n import Labels
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
    primed,
    theory_canvas,
)


def adas_adjustment_canvas(
    path: AdjustmentPath,
    *,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    x_max: float | None = None,
    y_max: float | None = None,
    extent: float = EXTENT,
    samples: int = DEFAULT_SAMPLES,
    width: float = THEORY_SIZE,
    height: float = THEORY_SIZE,
) -> Canvas:
    """Draw the adjustment of AS-AD as expectations catch up.

    Aggregate demand is fixed (a demand shock adds its new position, thin and solid). The
    starting supply curve stays heavy; every revision of the expected price level adds a thin
    dashed supply curve, and the last is the medium-run supply through natural output. The
    equilibria are A, A', A'', ... joined by arrows that slide along aggregate demand,
    ending at the medium-run equilibrium on the dashed vertical at natural output.
    """
    text = Labels(labels)
    equilibria = [step.equilibrium for step in path.steps] + [path.medium_run]
    right = x_max if x_max is not None else extent * max(e.output for e in equilibria)
    top = y_max if y_max is not None else extent * max(e.price for e in equilibria)
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
    last = path.steps[-1].model
    start = path.steps[0].model
    canvas.extend(
        curve(
            demand_curve(start.demand, right, top, samples),
            layer_id="macro.adas.demand",
            role="macro.curve.primary",
            label=text("adas.curve.demand"),
        )
    )
    if last.demand != start.demand:
        canvas.extend(
            curve(
                demand_curve(last.demand, right, top, samples),
                layer_id="macro.adas.demand.shifted",
                role="macro.curve.primary.shifted",
                label=text("adas.curve.demand_shifted"),
            )
        )
    supplies = [start.supply]
    for step in path.steps[1:]:
        if step.model.supply != supplies[-1]:
            supplies.append(step.model.supply)
    supplies.append(last.supply.with_expected_price(path.medium_run.price))
    for number, supply in enumerate(supplies):
        canvas.extend(
            curve(
                supply_curve(supply, right, top, samples),
                layer_id="macro.adas.supply" if number == 0 else f"macro.adas.supply.{number}",
                role="macro.curve.secondary" if number == 0 else "macro.curve.secondary.shifted",
                label=primed(text("adas.curve.supply"), number),
            )
        )
    natural = path.medium_run.output
    canvas.add(guide((natural, 0.0), (natural, HEADROOM * top), layer_id="macro.adas.natural"))
    canvas.add(
        axis_mark(
            "x", natural, text("adas.mark.natural_output"), layer_id="macro.adas.natural.mark"
        )
    )
    previous = None
    for number, equilibrium in enumerate(equilibria):
        point = (equilibrium.output, equilibrium.price)
        # Output is marked for the start and the impact only; the rest end at natural output.
        marked = (
            number < MARKED_OUTPUTS and abs(equilibrium.output - natural) > SAME_OUTPUT * natural
        )
        canvas.extend(
            drop_lines(
                point,
                x_label=primed(text("adas.mark.output"), number) if marked else None,
                y_label=primed(text("adas.mark.price"), number),
                layer_id=f"macro.adas.point.{number}.guide",
            )
        )
        canvas.extend(
            marked_point(
                point,
                point_name(0, prime=number),
                layer_id=f"macro.adas.point.{number}",
                role="macro.point" if number == 0 else "macro.point.shifted",
            )
        )
        if previous is not None:
            canvas.add(movement(previous, point, layer_id=f"macro.adas.path.{number}"))
        previous = point
    return canvas
