from __future__ import annotations

import pytest

from macro_viz import ValidationError
from macro_viz.adas import (
    AggregateDemand,
    AggregateSupply,
    ASADModel,
    Gap,
    Shock,
    analyze_demand_shock,
    analyze_supply_shock,
    employment,
)
from macro_viz.direction import Direction


def supply() -> AggregateSupply:
    return AggregateSupply.linear(1.0, 100, 0.6)


def natural_model() -> ASADModel:
    # autonomous 55 and kM = 45 make demand 100 at the expected price level
    return ASADModel(supply(), AggregateDemand(55, 45, 1))


def boom_model() -> ASADModel:
    return ASADModel(supply(), AggregateDemand(80, 45, 1))


def test_supply_passes_through_the_expected_price_at_natural_output() -> None:
    curve = supply()

    assert curve.price(100) == pytest.approx(1.0)
    assert curve.price(120) == pytest.approx(1.12)
    assert curve.price(50) < curve.price(100) < curve.price(150)
    assert curve.with_expected_price(1.5).price(100) == pytest.approx(1.5)
    assert curve.with_scale(0.8).price(100) == pytest.approx(0.8)


def test_demand_slopes_down_and_inverts_exactly() -> None:
    demand = AggregateDemand(55, 45, 1)

    assert demand.output(1.0) == pytest.approx(100)
    assert demand.output(2.0) < demand.output(1.0)
    assert demand.price(demand.output(1.3)) == pytest.approx(1.3)
    with pytest.raises(ValidationError):
        demand.price(55)


def test_equilibrium_solves_both_curves() -> None:
    model = boom_model()
    equilibrium = model.equilibrium()

    assert model.supply.price(equilibrium.output) == pytest.approx(equilibrium.price)
    assert model.demand.output(equilibrium.price) == pytest.approx(equilibrium.output)


def test_equilibrium_at_natural_output_has_no_gap() -> None:
    equilibrium = natural_model().equilibrium()

    assert equilibrium.gap is Gap.NONE
    assert equilibrium.output == pytest.approx(100)
    assert equilibrium.price == pytest.approx(equilibrium.expected_price)
    assert equilibrium.output_gap == pytest.approx(0, abs=1e-6)


def test_gap_classification() -> None:
    boom = boom_model().equilibrium()
    slump = ASADModel(supply(), AggregateDemand(30, 45, 1)).equilibrium()

    assert boom.gap is Gap.INFLATIONARY and boom.output_gap > 0
    assert boom.price > boom.expected_price
    assert slump.gap is Gap.RECESSIONARY and slump.output_gap < 0
    assert slump.price < slump.expected_price


def test_demand_shocks_move_output_and_prices_together() -> None:
    more = analyze_demand_shock(boom_model(), autonomous=100)
    less = analyze_demand_shock(boom_model(), money=30)

    assert more.shock is Shock.DEMAND
    assert (more.output_direction, more.price_direction) == (Direction.UP, Direction.UP)
    assert (less.output_direction, less.price_direction) == (Direction.DOWN, Direction.DOWN)
    assert more.after.output > more.before.output


def test_a_higher_expected_price_shifts_supply_up() -> None:
    shift = analyze_supply_shock(boom_model(), expected_price=1.2)

    assert shift.shock is Shock.SUPPLY
    assert (shift.output_direction, shift.price_direction) == (Direction.DOWN, Direction.UP)


def test_productivity_gain_shifts_supply_down_with_ambiguous_demand_side() -> None:
    shift = analyze_supply_shock(boom_model(), scale=0.8)

    assert (shift.output_direction, shift.price_direction) == (Direction.UP, Direction.DOWN)
    assert shift.post.supply.price(100) < shift.baseline.supply.price(100)
    assert shift.post.demand == shift.baseline.demand


def test_employment_is_output_over_productivity() -> None:
    assert employment(120, 2.0) == pytest.approx(60)
    assert employment(120, 3.0) < employment(120, 2.0)
    with pytest.raises(ValidationError):
        employment(120, 0)


@pytest.mark.parametrize(
    "build",
    [
        lambda: AggregateSupply.linear(1.0, 100, 1.0),
        lambda: AggregateSupply.linear(1.0, 100, 0),
        lambda: AggregateSupply(1.0, 100, lambda y: 2.0),
        lambda: AggregateSupply.linear(-1.0, 100, 0.5),
        lambda: AggregateDemand(0, 0, 1),
        lambda: AggregateDemand(0, 1, 0),
    ],
)
def test_invalid_curves_are_rejected(build: object) -> None:
    with pytest.raises(ValidationError):
        build()  # type: ignore[operator]


def test_a_convex_supply_curve_is_accepted() -> None:
    convex = AggregateSupply(1.0, 100, lambda y: (y / 100) ** 1.5)
    model = ASADModel(convex, AggregateDemand(40, 60, 1))
    equilibrium = model.equilibrium()

    assert convex.price(100) == pytest.approx(1.0)
    assert model.demand.output(equilibrium.price) == pytest.approx(equilibrium.output)
