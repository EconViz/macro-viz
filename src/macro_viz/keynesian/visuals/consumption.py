"""The consumption function with its intercept and slope triangle."""

from __future__ import annotations

from collections.abc import Mapping

from mosaickit import Canvas, MarkerLayer, TextLayer

from macro_viz.core.errors import ValidationError
from macro_viz.core.i18n import Labels
from macro_viz.keynesian.models import (
    ConsumptionFunction,
)
from macro_viz.keynesian.visuals._preset import LABEL_GAP, SLOPE_POSITION, SLOPE_RUN_SHARE
from macro_viz.visuals._theory import (
    DEFAULT_SAMPLES,
    HEADROOM,
    THEORY_SIZE,
    axis_mark,
    curve,
    guide,
    sample,
    theory_canvas,
    trim,
)


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
