from __future__ import annotations

import pytest
from mosaickit import MarkerLayer

from macro_viz import ValidationError
from macro_viz.money import MoneyDemand, MoneyMarket, MoneyMultiplier, analyze_supply_shift
from macro_viz.visuals import central_bank_money_canvas


def market() -> MoneyMarket:
    return MoneyMarket(MoneyDemand(100, lambda r: 0.9 - 0.12 * r, 6), 60)


def test_multiplier_is_one_over_c_plus_theta_times_one_minus_c() -> None:
    m = MoneyMultiplier(0.2, 0.1)

    assert m.base_ratio == pytest.approx(0.2 + 0.1 * 0.8)
    assert m.multiplier == pytest.approx(1 / 0.28)
    assert MoneyMultiplier(0.0, 0.1).multiplier == pytest.approx(10)


def test_rate_is_the_same_in_the_money_and_central_bank_money_markets() -> None:
    m = MoneyMultiplier(0.2, 0.1)
    base = m.market(market())

    assert base.supply == pytest.approx(60 * 0.28)
    assert base.equilibrium().rate == pytest.approx(market().equilibrium().rate)


@pytest.mark.parametrize("c, theta", [(-0.1, 0.1), (1.5, 0.1), (0.0, 0.0)])
def test_invalid_ratios_are_rejected(c: float, theta: float) -> None:
    with pytest.raises(ValidationError):
        MoneyMultiplier(c, theta)


def test_figure_is_labelled_with_h_and_marks_the_crossing() -> None:
    m = MoneyMultiplier(0.2, 0.1)
    canvas = central_bank_money_canvas(m, analyze_supply_shift(market(), 80))
    found = {layer.id: layer for layer in canvas.snapshot().layers}

    assert found["macro.money.supply.label"].text == "$H^s$"  # type: ignore[attr-defined]
    point = found["macro.money.equilibrium"]
    assert isinstance(point, MarkerLayer)
    assert point.points[0][0] == pytest.approx(60 * 0.28)
