"""The multiplier process behind a change in autonomous spending."""

from __future__ import annotations

from collections.abc import Mapping

from mosaickit import Canvas, Layer

from macro_viz.i18n import Labels
from macro_viz.keynesian.models import (
    DEFAULT_ROUNDS,
    AutonomousShift,
)
from macro_viz.visuals._theory import (
    DEFAULT_SAMPLES,
    EXTENT,
    THEORY_SIZE,
    curve,
    drop_lines,
    marked_point,
    movement,
    movement_label,
    point_name,
    sample,
    theory_canvas,
    trim,
)
from macro_viz.visuals.keynesian._base import _base_layers
from macro_viz.visuals.keynesian._preset import SHIFT_ARROW_POSITION


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
