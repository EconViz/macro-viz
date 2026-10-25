from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from mosaickit import MarkerLayer, PathLayer

from macro_viz import Config, ValidationError
from macro_viz.money import MoneyDemand, MoneyMarket, analyze_income_shift, analyze_supply_shift
from macro_viz.visuals import money_demand_canvas, money_market_canvas


@pytest.fixture(autouse=True)
def _reset_config() -> Iterator[None]:
    yield
    Config.reset()


def market() -> MoneyMarket:
    return MoneyMarket(MoneyDemand(100, lambda rate: 0.9 - 0.12 * rate, 6), supply=60)


def layers(canvas: object) -> dict[str, object]:
    return {layer.id: layer for layer in canvas.snapshot().layers}  # type: ignore[attr-defined]


def test_market_has_demand_supply_and_the_equilibrium() -> None:
    canvas = money_market_canvas(market(), title="Money market")
    found = layers(canvas)

    assert {
        "macro.money.demand",
        "macro.money.demand.label",
        "macro.money.supply",
        "macro.money.supply.label",
        "macro.money.equilibrium",
        "macro.money.equilibrium.guide.x.mark",
        "macro.money.equilibrium.guide.y.mark",
    } <= set(found)
    assert canvas.spec.title == "Money market"
    assert not any(".shifted" in layer_id for layer_id in found)
    point = found["macro.money.equilibrium"]
    assert isinstance(point, MarkerLayer)
    equilibrium = market().equilibrium()
    assert point.points[0] == pytest.approx((equilibrium.money, equilibrium.rate))


def test_supply_is_vertical_and_demand_slopes_down() -> None:
    found = layers(money_market_canvas(market()))
    supply, demand = found["macro.money.supply"], found["macro.money.demand"]

    assert isinstance(supply, PathLayer) and isinstance(demand, PathLayer)
    assert supply.path[0][0] == supply.path[-1][0] == 60
    assert all(b[0] < a[0] for a, b in zip(demand.path, demand.path[1:], strict=False))
    assert all(b[1] > a[1] for a, b in zip(demand.path, demand.path[1:], strict=False))


def test_income_shift_draws_the_new_demand_curve_and_one_mark_for_money() -> None:
    found = layers(money_market_canvas(analyze_income_shift(market(), 130)))

    assert "macro.money.demand.shifted" in found
    assert "macro.money.supply.shifted" not in found
    assert found["macro.money.demand.shifted"].role.endswith(".shifted")  # type: ignore[attr-defined]
    assert "macro.money.equilibrium.shifted.guide.x.mark" not in found
    assert "macro.money.equilibrium.shifted.guide.y.mark" in found
    assert "macro.money.shift" in found


def test_supply_shift_draws_the_new_supply_line_and_both_marks() -> None:
    found = layers(money_market_canvas(analyze_supply_shift(market(), 80)))

    assert "macro.money.supply.shifted" in found
    assert "macro.money.demand.shifted" not in found
    assert "macro.money.equilibrium.shifted.guide.x.mark" in found
    shifted = found["macro.money.equilibrium.shifted"]
    assert isinstance(shifted, MarkerLayer)
    assert shifted.points[0][0] == 80


def test_demand_figure_shows_both_quantities_at_one_rate() -> None:
    shift = analyze_income_shift(market(), 130)
    found = layers(money_demand_canvas(shift, rate=2.0))

    points = found["macro.money.rate.points"]
    assert isinstance(points, MarkerLayer)
    assert points.points[0] == pytest.approx((shift.baseline.demand.quantity(2.0), 2.0))
    assert points.points[1] == pytest.approx((shift.post.demand.quantity(2.0), 2.0))
    assert "macro.money.supply" not in found
    with pytest.raises(ValidationError):
        money_demand_canvas(shift, rate=99)
    with pytest.raises(ValidationError):
        money_demand_canvas(analyze_supply_shift(market(), 80))


def test_ranges_and_labels_follow_arguments_and_settings() -> None:
    wide = money_market_canvas(market(), x_max=500)
    renamed = layers(money_market_canvas(market(), labels={"money.curve.supply": "S"}))
    Config.from_dict({"macro": {"language": "zh-TW"}}).use()

    assert wide.spec.x_max == 500
    assert renamed["macro.money.supply.label"].text == "S"  # type: ignore[attr-defined]
    assert money_market_canvas(market()).spec.x_max == money_market_canvas(market()).spec.x_max


def test_figures_render_and_save(tmp_path: Path) -> None:
    for index, canvas in enumerate(
        (
            money_market_canvas(market()),
            money_market_canvas(analyze_supply_shift(market(), 80)),
            money_demand_canvas(analyze_income_shift(market(), 130)),
        )
    ):
        target = tmp_path / f"figure{index}.svg"
        canvas.save(target)
        assert target.stat().st_size > 0
