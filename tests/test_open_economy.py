from __future__ import annotations

import pytest
from mosaickit import MarkerLayer

from macro_viz import ValidationError
from macro_viz.direction import Direction
from macro_viz.keynesian import ConsumptionFunction, KeynesianCross
from macro_viz.open_economy import OpenEconomy, compare
from macro_viz.visuals import open_goods_canvas


def domestic() -> KeynesianCross:
    return KeynesianCross(ConsumptionFunction(20, 0.6), 20, 30, 20)


def model() -> OpenEconomy:
    return OpenEconomy(domestic(), 25, 0.2)


def test_equilibrium_and_multiplier() -> None:
    m = model()
    e = m.equilibrium()

    assert m.multiplier == pytest.approx(1 / (1 - 0.6 + 0.2))
    assert e.output == pytest.approx((domestic().autonomous_spending + 25) * m.multiplier)
    assert m.demand(e.output) == pytest.approx(e.output)


def test_open_multiplier_is_smaller_than_closed() -> None:
    assert model().multiplier < domestic().multiplier
    closed_like = OpenEconomy(domestic(), 0, 0.0)
    assert closed_like.multiplier == pytest.approx(domestic().multiplier)


def test_trade_balance_and_balanced_output() -> None:
    m = model()

    assert m.net_exports(m.balanced_trade_output()) == pytest.approx(0)
    assert m.trade_balance() == pytest.approx(25 - 0.2 * m.equilibrium().output)
    with pytest.raises(ValidationError):
        OpenEconomy(domestic(), 25, 0.0).balanced_trade_output()


def test_fiscal_expansion_raises_output_and_worsens_the_balance() -> None:
    shift = compare(model(), model().with_government(50))

    assert shift.output_direction is Direction.UP and shift.trade_direction is Direction.DOWN


def test_foreign_demand_raises_output_and_the_balance() -> None:
    shift = compare(model(), model().with_exports(40))

    assert shift.output_direction is Direction.UP and shift.trade_direction is Direction.UP


def test_figure_marks_the_equilibrium_and_balanced_trade_output() -> None:
    m = model()
    found = {
        layer.id: layer
        for layer in open_goods_canvas(compare(m, m.with_exports(40))).snapshot().layers
    }
    point = found["macro.keynesian.equilibrium"]

    assert isinstance(point, MarkerLayer)
    assert point.points[0][0] == pytest.approx(m.equilibrium().output)
    assert {"macro.open.balanced", "macro.keynesian.equilibrium.shifted"} <= set(found)
    plain = {
        layer.id for layer in open_goods_canvas(m, show_balanced_trade=False).snapshot().layers
    }
    assert "macro.open.balanced" not in plain
