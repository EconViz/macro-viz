"""Money-market figures: money demand, money supply, and the interest rate."""

from __future__ import annotations

from collections.abc import Mapping

from mosaickit import Canvas, Layer, MarkerLayer

from macro_viz.errors import ValidationError
from macro_viz.i18n import Labels
from macro_viz.money.models import Curve, MoneyDemand, MoneyMarket, MoneyMarketShift
from macro_viz.visuals._theory import (
    DEFAULT_SAMPLES,
    HEADROOM,
    THEORY_SIZE,
    curve,
    drop_lines,
    marked_point,
    point_name,
    shift_arrow,
    theory_canvas,
    trim,
)

MONEY_EXTENT = 1.25
"""Default length of the money axis as a multiple of the largest quantity drawn (a supply, or
the demand at a zero rate), so every curve ends inside the plot with room for its name."""

SAME_MONEY = 1e-9
"""Two money quantities closer than this share one mark on the axis."""

SHIFT_ARROW_RATE_SHARE = 0.7
"""Height of the arrow showing a curve's shift, as a share of the highest interest rate."""


def demand_curve(demand: MoneyDemand, samples: int) -> list[tuple[float, float]]:
    """Points ``(Y L(i), i)`` of the money demand curve for ``i`` from zero to ``rate_max``."""
    if isinstance(samples, bool) or not isinstance(samples, int) or samples < 2:
        raise ValidationError("samples must be an integer of at least 2")
    step = demand.rate_max / (samples - 1)
    return [(demand.quantity(k * step), k * step) for k in range(samples)]


def _supply_line(money: float, top: float) -> list[tuple[float, float]]:
    return [(money, 0.0), (money, top)]


def money_market_canvas(
    market: MoneyMarket | MoneyMarketShift,
    *,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    x_max: float | None = None,
    extent: float = MONEY_EXTENT,
    samples: int = DEFAULT_SAMPLES,
    width: float = THEORY_SIZE,
    height: float = THEORY_SIZE,
) -> Canvas:
    """Draw money demand, the money supply, and their crossing A.

    Given a ``MoneyMarketShift``, the moving curve is drawn twice (the old position heavy, the new
    one thin and dashed), the new equilibrium is A', and an arrow shows the shift. ``x_max``
    defaults to ``extent`` times the largest money supply drawn.
    """
    shift = market if isinstance(market, MoneyMarketShift) else None
    base = shift.baseline if shift is not None else market
    assert isinstance(base, MoneyMarket)
    post = shift.post if shift is not None else None
    markets = [base] + ([post] if post is not None else [])
    scale = max([m.supply for m in markets] + [m.demand.quantity(0.0) for m in markets])
    limit = x_max if x_max is not None else extent * scale
    top = base.demand.rate_max / HEADROOM
    text = Labels(labels)
    canvas = theory_canvas(
        limit,
        top,
        labels=text,
        x_label_id="money.axis.money",
        y_label_id="money.axis.rate",
        title=title,
        width=width,
        height=height,
    )
    canvas.extend(
        curve(
            trim(demand_curve(base.demand, samples), limit, top),
            layer_id="macro.money.demand",
            role="macro.curve.primary",
            label=text("money.curve.demand"),
        )
    )
    canvas.extend(
        curve(
            trim(_supply_line(base.supply, top), limit, top),
            layer_id="macro.money.supply",
            role="macro.curve.secondary",
            label=text("money.curve.supply"),
        )
    )
    start = base.equilibrium()
    start_point = (start.money, start.rate)
    canvas.extend(
        drop_lines(
            start_point,
            x_label=text("money.mark.money"),
            y_label=text("money.mark.rate"),
            layer_id="macro.money.equilibrium.guide",
        )
    )
    canvas.extend(marked_point(start_point, point_name(0), layer_id="macro.money.equilibrium"))
    if shift is not None and post is not None:
        canvas.extend(_shift_layers(shift, limit, top, samples, text))
    return canvas


def _shift_layers(
    shift: MoneyMarketShift, limit: float, top: float, samples: int, text: Labels
) -> list[Layer]:
    post = shift.post
    layers: list[Layer] = []
    moved_id = (
        "macro.money.demand.shifted"
        if shift.curve is Curve.DEMAND
        else "macro.money.supply.shifted"
    )
    rate = SHIFT_ARROW_RATE_SHARE * shift.baseline.demand.rate_max
    if shift.curve is Curve.DEMAND:
        points = trim(demand_curve(post.demand, samples), limit, top)
        label = text("money.curve.demand_shifted")
        role = "macro.curve.primary.shifted"
        arrow = (
            (shift.baseline.demand.quantity(rate), rate),
            (post.demand.quantity(rate), rate),
        )
    else:
        points = trim(_supply_line(post.supply, top), limit, top)
        label = text("money.curve.supply_shifted")
        role = "macro.curve.secondary.shifted"
        arrow = ((shift.baseline.supply, rate), (post.supply, rate))
    layers.extend(curve(points, layer_id=moved_id, role=role, label=label))
    layers.append(shift_arrow(*arrow, layer_id="macro.money.shift", extent=(limit, top)))
    end = post.equilibrium()
    end_point = (end.money, end.rate)
    same = abs(end.money - shift.baseline.equilibrium().money) < SAME_MONEY
    layers.extend(
        drop_lines(
            end_point,
            x_label=None if same else text("money.mark.money_shifted"),
            y_label=text("money.mark.rate_shifted"),
            layer_id="macro.money.equilibrium.shifted.guide",
        )
    )
    layers.extend(
        marked_point(
            end_point,
            point_name(0, prime=1),
            layer_id="macro.money.equilibrium.shifted",
            role="macro.point.shifted",
        )
    )
    return layers


def money_demand_canvas(
    shift: MoneyMarketShift,
    *,
    rate: float | None = None,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    x_max: float | None = None,
    extent: float = MONEY_EXTENT,
    samples: int = DEFAULT_SAMPLES,
    width: float = THEORY_SIZE,
    height: float = THEORY_SIZE,
) -> Canvas:
    """Draw money demand before and after a change in nominal income, at a given rate.

    At the interest rate ``rate`` (default: the baseline equilibrium rate) demand rises from
    ``M`` to ``M'``; the guides and axis marks show both quantities. The money supply is not
    drawn.
    """
    if shift.curve is not Curve.DEMAND:
        raise ValidationError("money_demand_canvas needs a shift of the demand curve")
    before, after = shift.baseline.demand, shift.post.demand
    level = shift.baseline.equilibrium().rate if rate is None else rate
    if not 0 <= level <= before.rate_max:
        raise ValidationError("rate must lie between zero and the highest rate")
    quantities = (before.quantity(level), after.quantity(level))
    scale = max(before.quantity(0.0), after.quantity(0.0))
    limit = x_max if x_max is not None else extent * scale
    top = before.rate_max / HEADROOM
    text = Labels(labels)
    canvas = theory_canvas(
        limit,
        top,
        labels=text,
        x_label_id="money.axis.money",
        y_label_id="money.axis.rate",
        title=title,
        width=width,
        height=height,
    )
    canvas.extend(
        curve(
            trim(demand_curve(before, samples), limit, top),
            layer_id="macro.money.demand",
            role="macro.curve.primary",
            label=text("money.curve.demand"),
        )
    )
    canvas.extend(
        curve(
            trim(demand_curve(after, samples), limit, top),
            layer_id="macro.money.demand.shifted",
            role="macro.curve.primary.shifted",
            label=text("money.curve.demand_shifted"),
        )
    )
    canvas.extend(
        drop_lines(
            (quantities[1], level),
            x_label=text("money.mark.money_shifted"),
            y_label=text("money.mark.rate"),
            layer_id="macro.money.rate.guide",
        )
    )
    canvas.extend(
        drop_lines(
            (quantities[0], level),
            x_label=text("money.mark.money"),
            y_label=None,
            layer_id="macro.money.rate.baseline.guide",
        )
    )
    canvas.add(
        MarkerLayer(
            ((quantities[0], level), (quantities[1], level)),
            id="macro.money.rate.points",
            role="macro.point",
            z_index=6,
        )
    )
    canvas.add(
        shift_arrow(
            (
                before.quantity(SHIFT_ARROW_RATE_SHARE * before.rate_max),
                SHIFT_ARROW_RATE_SHARE * before.rate_max,
            ),
            (
                after.quantity(SHIFT_ARROW_RATE_SHARE * before.rate_max),
                SHIFT_ARROW_RATE_SHARE * before.rate_max,
            ),
            layer_id="macro.money.shift",
            extent=(limit, top),
        )
    )
    return canvas
