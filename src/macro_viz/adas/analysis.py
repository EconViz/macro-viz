"""Comparative statics of the AS-AD model."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from macro_viz.adas.models import AggregateDemand, AggregateSupply, ASADEquilibrium, ASADModel
from macro_viz.direction import Direction


class Shock(str, Enum):
    """What moves: a demand curve or the supply curve."""

    DEMAND = "demand"
    SUPPLY = "supply"


@dataclass(frozen=True, slots=True)
class ASADShift:
    """Baseline and post-shock models with the direction of every change."""

    baseline: ASADModel
    post: ASADModel
    shock: Shock
    output_direction: Direction
    price_direction: Direction

    @property
    def before(self) -> ASADEquilibrium:
        return self.baseline.equilibrium()

    @property
    def after(self) -> ASADEquilibrium:
        return self.post.equilibrium()


def _shift(baseline: ASADModel, post: ASADModel, shock: Shock) -> ASADShift:
    before, after = baseline.equilibrium(), post.equilibrium()
    return ASADShift(
        baseline=baseline,
        post=post,
        shock=shock,
        output_direction=Direction.of(after.output - before.output),
        price_direction=Direction.of(after.price - before.price),
    )


def analyze_demand_shock(
    model: ASADModel, *, autonomous: float | None = None, money: float | None = None
) -> ASADShift:
    """Change autonomous demand (government spending, taxes) and/or nominal money.

    A rise in either shifts AD right; output and the price level both rise.
    """
    demand: AggregateDemand = model.demand
    if autonomous is not None:
        demand = demand.with_autonomous(autonomous)
    if money is not None:
        demand = demand.with_money(money)
    return _shift(model, model.with_demand(demand), Shock.DEMAND)


def analyze_supply_shock(
    model: ASADModel, *, expected_price: float | None = None, scale: float | None = None
) -> ASADShift:
    """Change the expected price level and/or the cost factor of aggregate supply.

    A higher expected price (or cost factor) shifts AS up: output falls and the price level rises.
    A productivity gain lowers the cost factor and shifts AS down.
    """
    supply: AggregateSupply = model.supply
    if expected_price is not None:
        supply = supply.with_expected_price(expected_price)
    if scale is not None:
        supply = supply.with_scale(scale)
    return _shift(model, model.with_supply(supply), Shock.SUPPLY)
