"""Stacked-panel derivation of aggregate demand."""

from __future__ import annotations

from collections.abc import Mapping

from mosaickit import CanvasGrid
from mosaickit.canvas.grid_link import GridLink

from macro_viz.errors import ValidationError
from macro_viz.i18n import Labels
from macro_viz.transmission import ADDerivation
from macro_viz.visuals._theory import (
    DEFAULT_SAMPLES,
    EXTENT,
    HEADROOM,
    axis_mark,
    curve,
    marked_point,
    point_name,
    theory_canvas,
    trim,
)
from macro_viz.visuals.islm import is_curve, lm_curve
from macro_viz.visuals.transmission._preset import DERIVATION_HEIGHT, DERIVATION_WIDTH
from macro_viz.visuals.transmission._shared import grid, indexed


def ad_derivation_canvas(
    derivation: ADDerivation,
    *,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    extent: float = EXTENT,
    samples: int = DEFAULT_SAMPLES,
    width: float = DERIVATION_WIDTH,
    height: float = DERIVATION_HEIGHT,
) -> CanvasGrid:
    """Draw IS-LM equilibria above the AD curve traced out as ``p`` changes."""
    states = derivation.states
    if min(state.rate for state in states) < 0:
        raise ValidationError("equilibrium rates must be non-negative to draw an AD derivation")
    text = Labels(labels)
    output_max = extent * max(state.output for state in states)
    price_max = max(state.price for state in states) / HEADROOM
    rate_limit = max(state.rate for state in states) / HEADROOM
    if rate_limit <= 0:
        raise ValidationError("at least one equilibrium rate must be positive")
    top = theory_canvas(
        output_max,
        rate_limit,
        labels=text,
        x_label_id="islm.axis.output",
        y_label_id="islm.axis.rate",
        title=title,
        width=width,
        height=height,
    )
    top.extend(
        curve(
            trim(is_curve(states[0].model, rate_limit, samples), output_max, rate_limit),
            layer_id="macro.transmission.ad.is",
            role="macro.curve.primary",
            label=text("islm.curve.is"),
        )
    )
    bottom = theory_canvas(
        output_max,
        price_max,
        labels=text,
        x_label_id="adas.axis.output",
        y_label_id="adas.axis.price",
        title=None,
        width=width,
        height=height,
    )
    bottom.extend(
        curve(
            sorted((state.output, state.price) for state in states),
            layer_id="macro.transmission.ad.curve",
            role="macro.curve.primary",
            label=text("adas.curve.demand"),
        )
    )
    links = []
    money_symbol = text("panels.var.money").strip("$")
    price_symbol = text("panels.var.price")
    for index, state in enumerate(states):
        top.extend(
            curve(
                trim(lm_curve(state.model, rate_limit, samples), output_max, rate_limit),
                layer_id=f"macro.transmission.ad.lm.{index}",
                role="macro.curve.secondary" if index == 0 else "macro.curve.secondary.shifted",
                label=text("panels.curve.lm").format(
                    money=money_symbol,
                    price=indexed(price_symbol, index).strip("$"),
                ),
            )
        )
        upper = (state.output, state.rate)
        lower = (state.output, state.price)
        top.extend(
            marked_point(
                upper,
                point_name(index),
                layer_id=f"macro.transmission.ad.islm.equilibrium.{index}",
            )
        )
        bottom.extend(
            marked_point(
                lower,
                point_name(index),
                layer_id=f"macro.transmission.ad.equilibrium.{index}",
            )
        )
        bottom.add(
            axis_mark(
                "y",
                state.price,
                indexed(text("adas.mark.price"), index),
                layer_id=f"macro.transmission.ad.price.{index}",
            )
        )
        links.append(GridLink(0, upper, 1, lower, role="macro.link"))
    return grid(((top,), (bottom,)), links, rows=2, cols=1)
