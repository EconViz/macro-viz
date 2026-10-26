"""The Keynesian cross: production line, demand curve and equilibrium A."""

from __future__ import annotations

from collections.abc import Mapping

from mosaickit import BraceLayer, Canvas

from macro_viz.i18n import Labels
from macro_viz.keynesian.models import (
    GoodsMarket,
    KeynesianCross,
)
from macro_viz.visuals._theory import (
    DEFAULT_SAMPLES,
    EXTENT,
    THEORY_SIZE,
    drop_lines,
    marked_point,
    point_name,
    theory_canvas,
)
from macro_viz.visuals.keynesian._base import _base_layers


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
