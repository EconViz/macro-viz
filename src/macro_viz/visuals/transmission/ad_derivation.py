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
    curve,
    drop_lines,
    marked_point,
    point_name,
    shift_arrow,
    theory_canvas,
)
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
)
from macro_viz.visuals.transmission._shared import grid, indexed, short_line_through


def _data_slope(points: list[tuple[float, float]]) -> float:
    (x0, y0), (x1, y1) = points[0], points[-1]
    return abs((y1 - y0) / (x1 - x0))


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
    # plot in display coordinates: A and B sit at the centre of each panel and the axis
    # lengths follow the screen slopes, so IS, LM and AD read as gentle lines
    aspect = height / width
    gap = abs(last.output - first.output)
    if gap <= 0:
        raise ValidationError("the solved outputs must differ to draw an AD derivation")
    span = gap / AD_GAP_SHARE
    lm_slope = _data_slope(lm_curve(first.model, 1.0, 2))
    rate_span = lm_slope * span * aspect / LM_DISPLAY_SLOPE
    ad_slope = abs(last.price - first.price) / gap
    price_span = ad_slope * span * aspect / AD_DISPLAY_SLOPE
    output_origin = (first.output + last.output) / 2 - span / 2
    rate_origin = (first.rate + last.rate) / 2 - rate_span / 2
    price_origin = (first.price + last.price) / 2 - price_span / 2

    def shown(output: float, vertical: float, origin: float) -> tuple[float, float]:
        return output - output_origin, vertical - origin

    rates = sorted({state.rate for state in states})
    top = theory_canvas(
        span,
        rate_span,
        labels=text,
        x_label_id="islm.axis.output",
        y_label_id="islm.axis.rate",
        title=title,
        width=width,
        height=height,
    )
    top.rising_names_above = True
    top.extend(
        curve(
            short_line_through(
                [shown(first.model.is_output(rate), rate, rate_origin) for rate in rates],
                span,
                rate_span,
                AD_ISLM_TAIL,
            ),
            layer_id="macro.transmission.ad.is",
            role="macro.curve.primary",
            label=text("islm.curve.is"),
        )
    )
    bottom = theory_canvas(
        span,
        price_span,
        labels=text,
        x_label_id="adas.axis.output",
        y_label_id="adas.axis.price",
        title=None,
        width=width,
        height=height,
    )
    bottom.extend(
        curve(
            short_line_through(
                [shown(state.output, state.price, price_origin) for state in states],
                span,
                price_span,
                AD_TAIL,
            ),
            layer_id="macro.transmission.ad.curve",
            role="macro.curve.secondary",
            label=text("adas.curve.demand"),
        )
    )
    # the money-market line moves left as the price rises, from A at its own rate
    top.add(
        shift_arrow(
            shown(first.output, first.rate, rate_origin),
            shown(last.model.lm_output(first.rate), first.rate, rate_origin),
            layer_id="macro.transmission.ad.lm.shift",
        )
    )
    links = []
    money_symbol = text("panels.var.money").strip("$")
    price_symbol = text("panels.var.price")
    for index, state in enumerate(states):
        top.extend(
            curve(
                short_line_through(
                    [shown(state.model.lm_output(rate), rate, rate_origin) for rate in rates],
                    span,
                    rate_span,
                    AD_LM_TAIL,
                ),
                layer_id=f"macro.transmission.ad.lm.{index}",
                role="macro.curve.secondary" if index == 0 else "macro.curve.secondary.shifted",
                label=text("panels.curve.lm").format(
                    money=money_symbol,
                    price=indexed(price_symbol, index).strip("$"),
                ),
            )
        )
        upper = shown(state.output, state.rate, rate_origin)
        lower = shown(state.output, state.price, price_origin)
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
        bottom.extend(
            drop_lines(
                lower,
                x_label=indexed(text("adas.mark.output"), index),
                y_label=indexed(text("adas.mark.price"), index),
                layer_id=f"macro.transmission.ad.drop.{index}",
            )
        )
        links.append(GridLink(0, upper, 1, lower, role="macro.link"))
    return grid(((top,), (bottom,)), links, rows=2, cols=1)
