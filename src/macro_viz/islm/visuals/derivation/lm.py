"""Side-by-side derivation of the LM curve."""

from __future__ import annotations

from collections.abc import Mapping
from functools import partial

from mosaickit import CanvasGrid
from mosaickit.diagram import PointLink, indexed, stack
from mosaickit.layout import View

from macro_viz.core.errors import ValidationError
from macro_viz.core.i18n import Labels
from macro_viz.islm.lm_derivation import LMDerivation
from macro_viz.visuals._diagram import LINK, PRIMARY, SECONDARY, panel
from macro_viz.visuals._theory import DEFAULT_SAMPLES, EXTENT, HEADROOM, point_name
from macro_viz.visuals.derivation._preset import (
    DERIVATION_WIDTH,
    LM_DERIVATION_DISPLAY_SLOPE,
    LM_DERIVATION_HEIGHT,
    LM_TAIL_SHARE,
    TAIL_LABEL_ABOVE,
    TAIL_LABEL_RIGHT,
)
from macro_viz.visuals.derivation._shared import SPACING, layer_id, parallel_liquidity_schedule

FIGURE = "lm"
"""Figure name in the layer ids of this derivation."""
PANEL_ROLE = "macro.curve.panel"
"""Role of the first liquidity-demand schedule, the baseline the others are compared with."""


def lm_derivation_canvas(
    derivation: LMDerivation,
    *,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    extent: float = EXTENT,
    samples: int = DEFAULT_SAMPLES,
    width: float = DERIVATION_WIDTH,
    height: float = LM_DERIVATION_HEIGHT,
) -> CanvasGrid:
    """Draw real-money markets beside the LM curve their equilibria trace out."""
    states = derivation.states
    if min(state.rate for state in states) < 0:
        raise ValidationError("equilibrium rates must be non-negative to draw an LM derivation")
    text = Labels(labels)
    money_max = extent * max(
        max(state.market.supply, state.market.demand.quantity(0.0)) for state in states
    )
    rate_max = max(state.market.demand.rate_max for state in states) / HEADROOM
    market = panel(
        text,
        "transmission.axis.real_money",
        "money.axis.rate",
        x_max=money_max,
        title=title,
        y_max=rate_max,
        width=width,
        height=height,
    )
    lm_points = [(state.output, state.rate) for state in states]
    (x0, y0), (x1, y1) = lm_points[0], lm_points[-1]
    data_slope = abs((y1 - y0) / (x1 - x0))
    output_span = LM_DERIVATION_DISPLAY_SLOPE * rate_max * width / (data_slope * height)
    lm = panel(
        text,
        "islm.axis.output",
        "islm.axis.rate",
        view=View(
            x_origin=(x0 + x1 - output_span) / 2,
            y_origin=0.0,
            x_span=output_span,
            y_span=rate_max,
        ),
        width=width,
        height=height,
    )
    name = partial(layer_id, FIGURE)
    supply = derivation.money_market.supply
    market.curve(
        name("supply"), [(supply, 0.0), (supply, HEADROOM * rate_max)], role=SECONDARY, trim=False
    )
    market.tail_label(
        name("supply", "tail-label"),
        name("supply"),
        text("transmission.curve.real_money_supply"),
        offset=TAIL_LABEL_ABOVE,
    )
    lm.line(
        name("curve"),
        lm_points,
        tail=LM_TAIL_SHARE,
        role=SECONDARY,
        label=text("islm.curve.lm"),
    )
    links, schedules = [], []
    for index, state in enumerate(states):
        left, right = (state.market.supply, state.rate), (state.output, state.rate)
        schedule = parallel_liquidity_schedule(left, money_max, rate_max, width, height)
        schedules.append(schedule)
        demand = name("demand", index)
        market.curve(demand, schedule, role=PANEL_ROLE if index == 0 else PRIMARY, trim=False)
        market.tail_label(
            f"{demand}.tail-label",
            demand,
            text("transmission.curve.liquidity_demand").format(index=index),
            offset=TAIL_LABEL_RIGHT,
        )
        market_point, lm_point = (
            name("market", "equilibrium", index),
            name("curve", "equilibrium", index),
        )
        market.point(market_point, left, point_name(index))
        market.axis_mark(
            "y",
            state.rate,
            indexed(text("money.mark.rate"), index),
            name=name("market", "rate", index),
        )
        market.guide((0.0, state.rate), left, name=name("market", "rate-guide", index))
        lm.point(lm_point, right, point_name(index))
        lm.axis_mark(
            "x", state.output, indexed(text("islm.mark.output"), index), name=name("output", index)
        )
        lm.guide((state.output, 0.0), right, name=name("curve", "output-guide", index))
        links.append(PointLink(0, market_point, 1, lm_point, role=LINK))
    market.arrow(
        name("demand", "shift"),
        (states[0].market.supply, states[0].rate),
        _shift_end(schedules[-1], states[0].rate),
    )
    return stack([market, lm], links, cols=2, spacing=SPACING)


def _shift_end(schedule: list[tuple[float, float]], rate: float) -> tuple[float, float]:
    """Where a horizontal line at ``rate`` meets the straight schedule through ``schedule``."""
    first, last = schedule[0], schedule[-1]
    slope = (last[1] - first[1]) / (last[0] - first[0])
    return (first[0] + (rate - first[1]) / slope, rate)
