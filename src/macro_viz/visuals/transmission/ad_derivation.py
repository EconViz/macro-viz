"""Stacked-panel derivation of aggregate demand."""

from __future__ import annotations

from collections.abc import Mapping
from functools import partial

from mosaickit import CanvasGrid
from mosaickit.diagram import PointLink, indexed, stack
from mosaickit.layout import View, centered_view

from macro_viz.errors import ValidationError
from macro_viz.i18n import Labels
from macro_viz.transmission import ADDerivation
from macro_viz.visuals._diagram import LINK, PRIMARY, SECONDARY, SHIFTED, panel
from macro_viz.visuals._theory import DEFAULT_SAMPLES, EXTENT, point_name
from macro_viz.visuals.islm import lm_curve
from macro_viz.visuals.transmission._preset import (
    AD_DERIVATION_HEIGHT,
    AD_DERIVATION_WIDTH,
    AD_DISPLAY_SLOPE,
    AD_GAP_SHARE,
    AD_ISLM_TAIL,
    AD_LM_TAIL,
    AD_TAIL,
    LM_DISPLAY_SLOPE,
    SHIFTED_NAME_SIDE,
)
from macro_viz.visuals.transmission._shared import SPACING, layer_id

FIGURE = "ad"
"""Figure name in the layer ids of this derivation."""


def _views(derivation: ADDerivation, width: float, height: float) -> tuple[View, View]:
    """The IS-LM and AD windows: A and B at the centre of each, axes following screen slopes.

    The lengths follow the screen slopes, so IS, LM and AD read as gentle lines.
    """
    first, last = derivation.states[0], derivation.states[-1]
    lm_chord = lm_curve(first.model, 1.0, 2)
    lm_slope = abs((lm_chord[-1][1] - lm_chord[0][1]) / (lm_chord[-1][0] - lm_chord[0][0]))
    islm = centered_view(
        [(first.output, first.rate), (last.output, last.rate)],
        display_slope=LM_DISPLAY_SLOPE,
        data_slope=lm_slope,
        gap_share=AD_GAP_SHARE,
        width=width,
        height=height,
    )
    adas = centered_view(
        [(first.output, first.price), (last.output, last.price)],
        display_slope=AD_DISPLAY_SLOPE,
        gap_share=AD_GAP_SHARE,
        width=width,
        height=height,
    )
    return islm, adas


def ad_derivation_canvas(
    derivation: ADDerivation,
    *,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    extent: float = EXTENT,
    samples: int = DEFAULT_SAMPLES,
    width: float = AD_DERIVATION_WIDTH,
    height: float = AD_DERIVATION_HEIGHT,
) -> CanvasGrid:
    """Draw IS-LM equilibria above the AD curve traced out as ``p`` changes."""
    states = derivation.states
    if min(state.rate for state in states) < 0:
        raise ValidationError("equilibrium rates must be non-negative to draw an AD derivation")
    text = Labels(labels)
    first, last = states[0], states[-1]
    if first.output == last.output:
        raise ValidationError("the solved outputs must differ to draw an AD derivation")
    islm_view, adas_view = _views(derivation, width, height)
    top = panel(
        text,
        "islm.axis.output",
        "islm.axis.rate",
        view=islm_view,
        title=title,
        width=width,
        height=height,
    )
    bottom = panel(
        text, "adas.axis.output", "adas.axis.price", view=adas_view, width=width, height=height
    )
    top.rising_names_upper_right = True
    rates = sorted({state.rate for state in states})
    name = partial(layer_id, FIGURE)
    top.line(
        name("is"),
        [(first.model.is_output(rate), rate) for rate in rates],
        tail=AD_ISLM_TAIL,
        role=PRIMARY,
        label=text("islm.curve.is"),
    )
    bottom.line(
        name("curve"),
        [(state.output, state.price) for state in states],
        tail=AD_TAIL,
        role=SECONDARY,
        label=text("adas.curve.demand"),
    )
    # the money-market line moves left as the price rises, from A at its own rate
    top.arrow(
        name("lm", "shift"),
        (first.output, first.rate),
        (last.model.lm_output(first.rate), first.rate),
    )
    money, price = text("panels.var.money").strip("$"), text("panels.var.price")
    links = []
    for index, state in enumerate(states):
        upper, lower = name("islm", "equilibrium", index), name("equilibrium", index)
        top.line(
            name("lm", index),
            [(state.model.lm_output(rate), rate) for rate in rates],
            tail=AD_LM_TAIL,
            side=None if index == 0 else SHIFTED_NAME_SIDE,
            role=SECONDARY if index == 0 else SHIFTED,
            label=text("panels.curve.lm").format(
                money=money, price=indexed(price, index).strip("$")
            ),
        )
        top.point(upper, (state.output, state.rate), point_name(index))
        bottom.point(lower, (state.output, state.price), point_name(index))
        bottom.drop(
            lower,
            x=indexed(text("adas.mark.output"), index),
            y=indexed(text("adas.mark.price"), index),
            name=name("drop", index),
        )
        links.append(PointLink(0, upper, 1, lower, role=LINK))
    return stack([top, bottom], links, spacing=SPACING)
