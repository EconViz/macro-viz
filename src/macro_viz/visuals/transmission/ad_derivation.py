"""Stacked-panel derivation of aggregate demand."""

from __future__ import annotations

from collections.abc import Mapping

from mosaickit import CanvasGrid
from mosaickit.canvas.grid_link import GridLink
from mosaickit.layout import View, centered_view, clip_polyline, extend_line_through

from macro_viz.errors import ValidationError
from macro_viz.i18n import Labels
from macro_viz.transmission import ADDerivation
from macro_viz.visuals._theory import (
    DEFAULT_SAMPLES,
    EXTENT,
    HEADROOM,
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
from macro_viz.visuals.transmission._shared import grid, indexed


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
    # plot in display coordinates: A and B sit at the centre of each panel and the axis
    # lengths follow the screen slopes, so IS, LM and AD read as gentle lines
    lm_chord = lm_curve(first.model, 1.0, 2)
    lm_slope = abs((lm_chord[-1][1] - lm_chord[0][1]) / (lm_chord[-1][0] - lm_chord[0][0]))
    kwargs = {"gap_share": AD_GAP_SHARE, "width": width, "height": height}
    upper_view = centered_view(
        [(first.output, first.rate), (last.output, last.rate)],
        display_slope=LM_DISPLAY_SLOPE,
        data_slope=lm_slope,
        **kwargs,
    )
    lower_view = centered_view(
        [(first.output, first.price), (last.output, last.price)],
        display_slope=AD_DISPLAY_SLOPE,
        **kwargs,
    )

    def line(
        view: View, points: list[tuple[float, float]], tail: float
    ) -> list[tuple[float, float]]:
        shown = [view.shift(point) for point in sorted(points)]
        return list(
            clip_polyline(
                extend_line_through(shown, before=tail),
                (0.0, HEADROOM * view.x_span),
                (0.0, HEADROOM * view.y_span),
            )
        )

    rates = sorted({state.rate for state in states})
    top = theory_canvas(
        upper_view.x_span,
        upper_view.y_span,
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
            line(upper_view, [(first.model.is_output(rate), rate) for rate in rates], AD_ISLM_TAIL),
            layer_id="macro.transmission.ad.is",
            role="macro.curve.primary",
            label=text("islm.curve.is"),
        )
    )
    bottom = theory_canvas(
        lower_view.x_span,
        lower_view.y_span,
        labels=text,
        x_label_id="adas.axis.output",
        y_label_id="adas.axis.price",
        title=None,
        width=width,
        height=height,
    )
    bottom.extend(
        curve(
            line(lower_view, [(state.output, state.price) for state in states], AD_TAIL),
            layer_id="macro.transmission.ad.curve",
            role="macro.curve.secondary",
            label=text("adas.curve.demand"),
        )
    )
    # the money-market line moves left as the price rises, from A at its own rate
    top.add(
        shift_arrow(
            upper_view.shift((first.output, first.rate)),
            upper_view.shift((last.model.lm_output(first.rate), first.rate)),
            layer_id="macro.transmission.ad.lm.shift",
        )
    )
    links = []
    money_symbol = text("panels.var.money").strip("$")
    price_symbol = text("panels.var.price")
    for index, state in enumerate(states):
        top.extend(
            curve(
                line(
                    upper_view, [(state.model.lm_output(rate), rate) for rate in rates], AD_LM_TAIL
                ),
                layer_id=f"macro.transmission.ad.lm.{index}",
                role="macro.curve.secondary" if index == 0 else "macro.curve.secondary.shifted",
                label=text("panels.curve.lm").format(
                    money=money_symbol,
                    price=indexed(price_symbol, index).strip("$"),
                ),
            )
        )
        upper = upper_view.shift((state.output, state.rate))
        lower = lower_view.shift((state.output, state.price))
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
