"""Three-panel derivation of the IS curve."""

from __future__ import annotations

from collections.abc import Mapping

from mosaickit import CanvasGrid, PathLayer, TextLayer
from mosaickit.canvas.grid_link import GridLink

from macro_viz.errors import ValidationError
from macro_viz.i18n import Labels
from macro_viz.transmission import ISDerivation
from macro_viz.visuals._theory import (
    DEFAULT_SAMPLES,
    axis_mark,
    curve,
    drop_lines,
    guide,
    marked_point,
    point_name,
    sample,
    theory_canvas,
    trim,
)
from macro_viz.visuals.transmission._preset import (
    DERIVATION_HEIGHT,
    DERIVATION_WIDTH,
    INVESTMENT_TO_IS_SLOPE,
)
from macro_viz.visuals.transmission._shared import axis_with_upper_tail, grid, indexed, line_through


def is_derivation_canvas(
    derivation: ISDerivation,
    *,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    samples: int = DEFAULT_SAMPLES,
    width: float = DERIVATION_WIDTH,
    height: float = DERIVATION_HEIGHT,
) -> CanvasGrid:
    """Draw AE-Y, R-Y, and R-I panels in the fixed three-quadrant IS derivation."""
    states = derivation.states
    if min(state.rate for state in states) < 0:
        raise ValidationError("rates must be non-negative to draw an IS derivation")
    text = Labels(labels)
    outputs = [state.output for state in states]
    investments = [state.investment for state in states]
    rates = [state.rate for state in states]
    output_max = axis_with_upper_tail(outputs)
    propensity = derivation.goods_at_zero_rate.consumption.propensity
    investment_max = max(
        axis_with_upper_tail(investments),
        INVESTMENT_TO_IS_SLOPE * (1.0 - propensity) * output_max,
    )
    if min(state.investment for state in states) <= 0:
        raise ValidationError("investment must stay positive to draw an IS derivation")
    rate_max = axis_with_upper_tail(rates)
    if rate_max <= 0:
        raise ValidationError("at least one rate must be positive")
    goods = theory_canvas(
        output_max,
        output_max,
        labels=text,
        x_label_id="keynesian.axis.income",
        y_label_id="transmission.axis.ae",
        title=title,
        width=width,
        height=height,
    )
    diagonal = trim(((0.0, 0.0), (output_max, output_max)), output_max, output_max)
    goods.add(
        PathLayer(tuple(diagonal), id="macro.transmission.is.production", role="macro.line45")
    )
    lower = theory_canvas(
        output_max,
        rate_max,
        labels=text,
        x_label_id="islm.axis.output",
        y_label_id="transmission.axis.real_rate",
        title=None,
        width=width,
        height=height,
    )
    lower.extend(
        curve(
            line_through([(state.output, state.rate) for state in states], output_max, rate_max),
            layer_id="macro.transmission.is.curve",
            role="macro.curve.secondary",
            label=text("islm.curve.is"),
        )
    )
    investment = theory_canvas(
        investment_max,
        rate_max,
        labels=text,
        x_label_id="transmission.axis.investment",
        y_label_id="transmission.axis.real_rate",
        title=None,
        width=width,
        height=height,
    )
    investment.extend(
        curve(
            line_through(
                [(state.investment, state.rate) for state in states], investment_max, rate_max
            ),
            layer_id="macro.transmission.is.investment",
            role="macro.curve.secondary",
            label=text("transmission.curve.investment"),
        )
    )
    links: list[GridLink] = []
    for index, state in enumerate(states):
        points = trim(sample(state.market.demand, 0.0, output_max, samples), output_max, output_max)
        goods_role = "macro.curve.panel" if index == 0 else "macro.curve.primary"
        goods.extend(
            curve(
                points,
                layer_id=f"macro.transmission.is.goods.{index}",
                role=goods_role,
            )
        )
        goods.add(
            TextLayer(
                max(points, key=lambda point: (point[0], point[1])),
                text("transmission.curve.ae_equation").format(
                    rate=indexed(text("transmission.mark.real_rate"), index).strip("$"),
                ),
                offset=(8.0, 0.0),
                anchor="left",
                id=f"macro.transmission.is.goods.{index}.tail-label",
                role=goods_role,
                z_index=7,
            )
        )
        goods.extend(
            marked_point(
                (state.output, state.output),
                point_name(index),
                layer_id=f"macro.transmission.is.goods.equilibrium.{index}",
            )
        )
        goods.extend(
            drop_lines(
                (state.output, state.output),
                x_label=indexed(text("keynesian.mark.output"), index),
                y_label=None,
                layer_id=f"macro.transmission.is.goods.guide.{index}",
            )
        )
        lower.extend(
            marked_point(
                (state.output, state.rate),
                point_name(index),
                layer_id=f"macro.transmission.is.curve.equilibrium.{index}",
            )
        )
        lower.add(
            guide(
                (0.0, state.rate),
                (state.output, state.rate),
                layer_id=f"macro.transmission.is.curve.rate-guide.{index}",
            )
        )
        lower.add(
            guide(
                (state.output, 0.0),
                (state.output, rate_max),
                layer_id=f"macro.transmission.is.curve.output-guide.{index}",
            )
        )
        lower.add(
            axis_mark(
                "x",
                state.output,
                indexed(text("keynesian.mark.output"), index),
                layer_id=f"macro.transmission.is.output.{index}",
            )
        )
        lower.add(
            axis_mark(
                "y",
                state.rate,
                indexed(text("transmission.mark.real_rate"), index),
                layer_id=f"macro.transmission.is.rate.{index}",
            )
        )
        investment.extend(
            marked_point(
                (state.investment, state.rate),
                point_name(index),
                layer_id=f"macro.transmission.is.investment.equilibrium.{index}",
            )
        )
        investment.extend(
            drop_lines(
                (state.investment, state.rate),
                x_label=indexed(text("transmission.axis.investment"), index),
                y_label=None,
                layer_id=f"macro.transmission.is.investment.guide.{index}",
            )
        )
        links.append(
            GridLink(
                1,
                (state.output, state.rate),
                2,
                (state.investment, state.rate),
                role="macro.link",
            )
        )
    return grid(((goods, None), (lower, investment)), links, rows=2, cols=2)
