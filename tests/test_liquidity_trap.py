from __future__ import annotations

import pytest
from mosaickit import MarkerLayer, PathLayer

from macro_viz.direction import Direction
from macro_viz.islm import ISLM, analyze_monetary_policy
from macro_viz.money import MoneyDemand, MoneyMarket, analyze_supply_shift
from macro_viz.visuals import islm_canvas, money_market_canvas


def demand(zero_bound: bool = True) -> MoneyDemand:
    return MoneyDemand(100, lambda r: 0.9 - 0.12 * r, 6, zero_bound=zero_bound)


def test_money_beyond_the_zero_rate_demand_leaves_the_rate_at_zero() -> None:
    market = MoneyMarket(demand(), 130)

    assert market.equilibrium().rate == 0.0
    shift = analyze_supply_shift(market, 160)
    assert shift.rate_direction is Direction.NONE
    assert analyze_supply_shift(MoneyMarket(demand(), 60), 80).rate_direction is Direction.DOWN


def test_without_the_bound_the_same_supply_is_rejected() -> None:
    from macro_viz import ValidationError

    with pytest.raises(ValidationError):
        MoneyMarket(demand(False), 130).equilibrium()


def trap() -> ISLM:
    return ISLM(80, 25, 60, 0.5, 8, zero_bound=True)


def test_is_crossing_the_flat_lm_gives_a_zero_rate_and_money_does_not_help() -> None:
    model = trap()
    shift = analyze_monetary_policy(model, 90)

    assert model.equilibrium().rate == 0.0
    assert model.equilibrium().output == pytest.approx(model.is_output(0.0))
    assert shift.output_direction is Direction.NONE and shift.rate_direction is Direction.NONE


def test_flat_lm_figure_has_a_flat_piece_and_no_shifted_point() -> None:
    canvas = islm_canvas(analyze_monetary_policy(trap(), 90), x_max=300)
    found = {layer.id: layer for layer in canvas.snapshot().layers}
    lm = found["macro.islm.lm"]

    assert isinstance(lm, PathLayer)
    assert lm.path[0][1] == lm.path[1][1] == 0.0
    assert "macro.islm.equilibrium.shifted" not in found
    assert isinstance(found["macro.islm.equilibrium"], MarkerLayer)


def test_money_figure_draws_demand_flat_at_zero() -> None:
    canvas = money_market_canvas(MoneyMarket(demand(), 130), x_max=600)
    found = {layer.id: layer for layer in canvas.snapshot().layers}
    path = found["macro.money.demand"]

    assert isinstance(path, PathLayer)
    assert any(p[1] == 0.0 and p[0] > 90 for p in path.path)
