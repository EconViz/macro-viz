"""Comparative statics of the money market."""

from __future__ import annotations

from macro_viz.core.direction import Direction
from macro_viz.money.models import Curve, MoneyMarket, MoneyMarketShift


def _shift(baseline: MoneyMarket, post: MoneyMarket, curve: Curve) -> MoneyMarketShift:
    before, after = baseline.equilibrium(), post.equilibrium()
    return MoneyMarketShift(
        baseline=baseline,
        post=post,
        curve=curve,
        rate_direction=Direction.of(after.rate - before.rate),
        money_direction=Direction.of(after.money - before.money),
    )


def analyze_income_shift(market: MoneyMarket, nominal_income: float) -> MoneyMarketShift:
    """Change nominal income: demand shifts and supply stays; higher income raises ``i``."""
    return _shift(market, market.with_nominal_income(nominal_income), Curve.DEMAND)


def analyze_supply_shift(market: MoneyMarket, supply: float) -> MoneyMarketShift:
    """Change the money supply: the vertical supply line shifts; more money lowers ``i``."""
    return _shift(market, market.with_supply(supply), Curve.SUPPLY)
