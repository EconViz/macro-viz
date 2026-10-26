"""Three-panel derivation of the IS curve."""

from __future__ import annotations

from collections.abc import Mapping
from functools import partial

from mosaickit import CanvasGrid
from mosaickit.canvas.grid_link import GridLink
from mosaickit.diagram import indexed

from macro_viz.errors import ValidationError
from macro_viz.i18n import Labels
from macro_viz.transmission import ISDerivation
from macro_viz.visuals._diagram import LINK, PRIMARY, SECONDARY, panel
from macro_viz.visuals._theory import DEFAULT_SAMPLES, point_name, sample, trim
from macro_viz.visuals.transmission._preset import (
    DERIVATION_HEIGHT,
    DERIVATION_WIDTH,
    INVESTMENT_TO_IS_SLOPE,
    PRODUCTION_Z_INDEX,
    TAIL_LABEL_RIGHT,
)
from macro_viz.visuals.transmission._shared import (
    axis_with_upper_tail,
    grid,
    layer_id,
    line_through,
)

FIGURE = "is"
"""Figure name in the layer ids of this derivation."""
PRODUCTION_ROLE = "macro.line45"
"""Role of the 45-degree line along which output equals aggregate expenditure."""
PANEL_ROLE = "macro.curve.panel"
"""Role of the first expenditure schedule, the baseline the others are compared with."""


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
    goods = panel(
        text,
        "keynesian.axis.income",
        "transmission.axis.ae",
        x_max=output_max,
        y_max=output_max,
        title=title,
        width=width,
        height=height,
    )
    lower = panel(
        text,
        "islm.axis.output",
        "transmission.axis.real_rate",
        x_max=output_max,
        y_max=rate_max,
        width=width,
        height=height,
    )
    investment = panel(
        text,
        "transmission.axis.investment",
        "transmission.axis.real_rate",
        x_max=investment_max,
        y_max=rate_max,
        width=width,
        height=height,
    )
    name = partial(layer_id, FIGURE)
    rate_symbol = text("transmission.mark.real_rate")
    goods.curve(
        name("production"),
        ((0.0, 0.0), (output_max, output_max)),
        role=PRODUCTION_ROLE,
        z_index=PRODUCTION_Z_INDEX,
    )
    lower.curve(
        name("curve"),
        line_through([(state.output, state.rate) for state in states], output_max, rate_max),
        role=SECONDARY,
        label=text("islm.curve.is"),
        trim=False,
    )
    investment.curve(
        name("investment"),
        line_through(
            [(state.investment, state.rate) for state in states], investment_max, rate_max
        ),
        role=SECONDARY,
        label=text("transmission.curve.investment"),
        trim=False,
    )
    links = []
    for index, state in enumerate(states):
        point_label = point_name(len(states) - index - 1)
        output_mark = indexed(text("keynesian.mark.output"), index)
        schedule = name("goods", index)
        goods.curve(
            schedule,
            trim(sample(state.market.demand, 0.0, output_max, samples), output_max, output_max),
            role=PANEL_ROLE if index == len(states) - 1 else PRIMARY,
            trim=False,
        )
        goods.tail_label(
            f"{schedule}.tail-label",
            schedule,
            text("transmission.curve.ae_equation").format(
                rate=indexed(rate_symbol, index).strip("$")
            ),
            offset=TAIL_LABEL_RIGHT,
        )
        on_goods, on_lower, on_investment = (
            name("goods", "equilibrium", index),
            name("curve", "equilibrium", index),
            name("investment", "equilibrium", index),
        )
        goods.point(on_goods, (state.output, state.output), point_label)
        goods.drop(on_goods, x=output_mark, name=name("goods", "guide", index))
        lower.point(on_lower, (state.output, state.rate), point_label)
        lower.guide((0.0, state.rate), on_lower, name=name("curve", "rate-guide", index))
        lower.guide(
            (state.output, 0.0), (state.output, rate_max), name=name("curve", "output-guide", index)
        )
        lower.axis_mark("x", state.output, output_mark, name=name("output", index))
        lower.axis_mark("y", state.rate, indexed(rate_symbol, index), name=name("rate", index))
        investment.point(on_investment, (state.investment, state.rate), point_label)
        investment.drop(
            on_investment,
            x=indexed(text("transmission.axis.investment"), index),
            name=name("investment", "guide", index),
        )
        links.append(GridLink(1, lower.at(on_lower), 2, investment.at(on_investment), role=LINK))
    return grid(
        ((goods.canvas(), None), (lower.canvas(), investment.canvas())), links, rows=2, cols=2
    )
