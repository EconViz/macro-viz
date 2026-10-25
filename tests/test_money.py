from __future__ import annotations

import pytest

from macro_viz import ValidationError
from macro_viz.direction import Direction
from macro_viz.money import (
    Curve,
    MoneyDemand,
    MoneyMarket,
    analyze_income_shift,
    analyze_supply_shift,
)


def liquidity(rate: float) -> float:
    return 0.9 - 0.12 * rate


def market() -> MoneyMarket:
    return MoneyMarket(MoneyDemand(100, liquidity, rate_max=6), supply=60)


def test_equilibrium_rate_solves_demand_equals_supply() -> None:
    equilibrium = market().equilibrium()

    assert equilibrium.rate == pytest.approx((0.9 - 0.6) / 0.12)
    assert equilibrium.money == 60
    assert market().demand.quantity(equilibrium.rate) == pytest.approx(60)


def test_demand_is_nominal_income_times_liquidity() -> None:
    demand = MoneyDemand(100, liquidity, rate_max=6)

    assert demand.quantity(0) == pytest.approx(90)
    assert demand.quantity(2) == pytest.approx(100 * liquidity(2))
    assert demand.quantity(5) < demand.quantity(1)
    assert demand.rate(demand.quantity(3.3)) == pytest.approx(3.3)


def test_higher_income_shifts_demand_right_and_raises_the_rate() -> None:
    shift = analyze_income_shift(market(), 130)

    assert shift.curve is Curve.DEMAND
    assert shift.rate_direction is Direction.UP
    assert shift.money_direction is Direction.NONE
    assert shift.rate_change > 0
    assert shift.post.demand.quantity(2) > shift.baseline.demand.quantity(2)


def test_more_money_shifts_supply_right_and_lowers_the_rate() -> None:
    shift = analyze_supply_shift(market(), 80)

    assert shift.curve is Curve.SUPPLY
    assert shift.rate_direction is Direction.DOWN
    assert shift.money_direction is Direction.UP
    assert shift.money_change == 20
    assert shift.post.equilibrium().rate == pytest.approx((0.9 - 0.8) / 0.12)


def test_less_money_and_lower_income_reverse_the_directions() -> None:
    assert analyze_supply_shift(market(), 50).rate_direction is Direction.UP
    assert analyze_income_shift(market(), 80).rate_direction is Direction.DOWN


def test_an_unreachable_supply_is_rejected() -> None:
    with pytest.raises(ValidationError):
        MoneyMarket(MoneyDemand(100, liquidity, rate_max=6), supply=95).equilibrium()
    with pytest.raises(ValidationError):
        MoneyMarket(MoneyDemand(100, liquidity, rate_max=6), supply=10).equilibrium()


@pytest.mark.parametrize("income, rate_max", [(0, 6), (-1, 6), (100, 0), (float("nan"), 6)])
def test_invalid_demand_is_rejected(income: float, rate_max: float) -> None:
    with pytest.raises(ValidationError):
        MoneyDemand(income, liquidity, rate_max)


def test_liquidity_must_fall_with_the_rate() -> None:
    with pytest.raises(ValidationError):
        MoneyDemand(100, lambda rate: 0.5 + 0.01 * rate, 6)
    with pytest.raises(ValidationError):
        MoneyMarket(MoneyDemand(100, liquidity, 6), supply=0)
