"""Side-by-side derivation of the LM curve."""

from __future__ import annotations

from collections.abc import Mapping

from mosaickit import CanvasGrid, TextLayer
from mosaickit.canvas.grid_link import GridLink

from macro_viz.errors import ValidationError
from macro_viz.i18n import Labels
from macro_viz.transmission import LMDerivation
from macro_viz.visuals._theory import (
    DEFAULT_SAMPLES,
    EXTENT,
    HEADROOM,
    axis_mark,
    curve,
    guide,
    marked_point,
    point_name,
    shift_arrow,
    theory_canvas,
)
from macro_viz.visuals.transmission._preset import (
    DERIVATION_WIDTH,
    LM_DERIVATION_HEIGHT,
    LM_TAIL_SHARE,
)
from macro_viz.visuals.transmission._shared import (
    grid,
    indexed,
    parallel_liquidity_schedule,
    tailed_line,
)


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
    output_max = extent * max(state.output for state in states)
    market = theory_canvas(
        money_max,
        rate_max,
        labels=text,
        x_label_id="transmission.axis.real_money",
        y_label_id="money.axis.rate",
        title=title,
        width=width,
        height=height,
    )
    supply_path = (
        (derivation.money_market.supply, 0.0),
        (derivation.money_market.supply, HEADROOM * rate_max),
    )
    market.extend(
        curve(
            supply_path,
            layer_id="macro.transmission.lm.supply",
            role="macro.curve.secondary",
        )
    )
    market.add(
        TextLayer(
            supply_path[-1],
            text("transmission.curve.real_money_supply"),
            offset=(0.0, 8.0),
            anchor="bottom",
            id="macro.transmission.lm.supply.tail-label",
            role="macro.curve.secondary",
            z_index=7,
        )
    )
    lm = theory_canvas(
        output_max,
        rate_max,
        labels=text,
        x_label_id="islm.axis.output",
        y_label_id="islm.axis.rate",
        title=None,
        width=width,
        height=height,
    )
    lm.extend(
        curve(
            tailed_line(
                [(state.output, state.rate) for state in states],
                output_max,
                rate_max,
                LM_TAIL_SHARE,
            ),
            layer_id="macro.transmission.lm.curve",
            role="macro.curve.secondary",
            label=text("islm.curve.lm"),
        )
    )
    links: list[GridLink] = []
    demand_paths: list[list[tuple[float, float]]] = []
    for index, state in enumerate(states):
        left = (state.market.supply, state.rate)
        right = (state.output, state.rate)
        demand_path = parallel_liquidity_schedule(left, money_max, rate_max, width, height)
        demand_paths.append(demand_path)
        demand_role = "macro.curve.panel" if index == 0 else "macro.curve.primary"
        market.extend(
            curve(
                demand_path,
                layer_id=f"macro.transmission.lm.demand.{index}",
                role=demand_role,
            )
        )
        market.add(
            TextLayer(
                max(demand_path, key=lambda point: (point[0], point[1])),
                text("transmission.curve.liquidity_demand").format(index=index),
                offset=(8.0, 0.0),
                anchor="left",
                id=f"macro.transmission.lm.demand.{index}.tail-label",
                role=demand_role,
                z_index=7,
            )
        )
        market.extend(
            marked_point(
                left,
                point_name(index),
                layer_id=f"macro.transmission.lm.market.equilibrium.{index}",
            )
        )
        market.add(
            axis_mark(
                "y",
                state.rate,
                indexed(text("money.mark.rate"), index),
                layer_id=f"macro.transmission.lm.market.rate.{index}",
            )
        )
        market.add(
            guide(
                (0.0, state.rate),
                left,
                layer_id=f"macro.transmission.lm.market.rate-guide.{index}",
            )
        )
        lm.extend(
            marked_point(
                right,
                point_name(index),
                layer_id=f"macro.transmission.lm.curve.equilibrium.{index}",
            )
        )
        lm.add(
            axis_mark(
                "x",
                state.output,
                indexed(text("islm.mark.output"), index),
                layer_id=f"macro.transmission.lm.output.{index}",
            )
        )
        lm.add(
            guide(
                (state.output, 0.0),
                right,
                layer_id=f"macro.transmission.lm.curve.output-guide.{index}",
            )
        )
        links.append(GridLink(0, left, 1, right, role="macro.link"))
    shift_rate = states[0].rate
    shifted_first, shifted_last = demand_paths[-1][0], demand_paths[-1][-1]
    shifted_slope = (shifted_last[1] - shifted_first[1]) / (shifted_last[0] - shifted_first[0])
    shift_end = (
        shifted_first[0] + (shift_rate - shifted_first[1]) / shifted_slope,
        shift_rate,
    )
    market.add(
        shift_arrow(
            (states[0].market.supply, shift_rate),
            shift_end,
            layer_id="macro.transmission.lm.demand.shift",
        )
    )
    return grid(((market, lm),), links, rows=1, cols=2)
