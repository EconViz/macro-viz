"""IS, LM, AD, and AS derivations share one solved value across their panels."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from mosaickit import ArrowLayer, CanvasGrid, MarkerLayer, PointLabelLayer, TextLayer

from macro_viz import Config, ValidationError
from macro_viz.islm import ISLM
from macro_viz.keynesian import ConsumptionFunction, KeynesianCross
from macro_viz.money import MoneyDemand, MoneyMarket
from macro_viz.panels import LinearFunction, MacroEconomy, QuadraticProduction
from macro_viz.transmission import ADDerivation, ASDerivation, ISDerivation, LMDerivation
from macro_viz.visuals import (
    ad_derivation_canvas,
    as_derivation_canvas,
    is_derivation_canvas,
    lm_derivation_canvas,
)
from macro_viz.visuals.transmission._preset import (
    AS_SRAS_DISPLAY_SLOPE,
    LM_DERIVATION_DISPLAY_SLOPE,
)


@pytest.fixture(autouse=True)
def _reset_config() -> Iterator[None]:
    yield
    Config.reset()


@pytest.fixture
def goods() -> KeynesianCross:
    return KeynesianCross(ConsumptionFunction(5.0, 0.6), 30.0, 20.0, 5.0)


@pytest.fixture
def money() -> MoneyMarket:
    return MoneyMarket(MoneyDemand(20.0, lambda rate: 2.0 - 0.1 * rate, 10.0), 30.0)


@pytest.fixture
def economy() -> MacroEconomy:
    return MacroEconomy(
        QuadraticProduction(3.0, 0.2, 1.0),
        LinearFunction(0.4, 0.25),
        1.0,
        1.0,
    )


def test_is_states_are_the_same_goods_equilibria_drawn_on_is(goods: KeynesianCross) -> None:
    derivation = ISDerivation(goods, 4.0, (2.0, 6.0))

    for state in derivation.states:
        assert state.output == pytest.approx(state.market.equilibrium().output)
        assert state.market.investment == pytest.approx(goods.investment - 4.0 * state.rate)


def test_lm_states_are_the_same_money_equilibria_drawn_on_lm(money: MoneyMarket) -> None:
    derivation = LMDerivation(money, (20.0, 25.0))

    for state in derivation.states:
        assert state.market.demand.nominal_income == state.output
        assert state.market.demand.quantity(state.rate) == pytest.approx(state.market.supply)


def test_lm_derivation_centres_points_and_uses_a_gentle_slope(money: MoneyMarket) -> None:
    grid = lm_derivation_canvas(LMDerivation(money, (20.0, 25.0)))
    market_spec, market_points = _panel(grid, 0)
    spec, points = _panel(grid, 1)
    (x0, x1), (y0, y1) = spec.x_range, spec.y_range  # type: ignore[attr-defined]
    (ax, ay), (bx, by) = sorted(points)

    assert (ax + bx) / 2 == pytest.approx((x0 + x1) / 2)
    assert spec.y_range == market_spec.y_range  # type: ignore[attr-defined]
    assert sorted(point[1] for point in points) == pytest.approx(
        sorted(point[1] for point in market_points)
    )
    screen_slope = (
        abs((by - ay) / (bx - ax)) / ((y1 - y0) / (x1 - x0)) * (spec.height / spec.width)  # type: ignore[attr-defined]
    )
    assert screen_slope == pytest.approx(LM_DERIVATION_DISPLAY_SLOPE, rel=0.05)


def test_ad_states_use_one_nominal_money_stock() -> None:
    derivation = ADDerivation(ISLM(40.0, 4.0, 10.0, 0.5, 2.0), 20.0, (1.0, 2.0))

    for state in derivation.states:
        assert state.model.real_money == pytest.approx(20.0 / state.price)
        equilibrium = state.model.equilibrium()
        assert (state.output, state.rate) == pytest.approx((equilibrium.output, equilibrium.rate))


def test_as_states_are_consistent_across_all_three_panels(economy: MacroEconomy) -> None:
    derivation = ASDerivation(economy, (0.8, 1.0, 1.2))

    for state in derivation.states:
        assert economy.labor_demand(state.employment, state.price) == pytest.approx(state.wage)
        assert economy.labor_supply_wage(state.employment) == pytest.approx(state.wage)
        assert economy.production.output(state.employment, economy.capital) == pytest.approx(
            state.output
        )


def test_as_primary_demand_extends_left_and_point_names_stay_on_markers(
    economy: MacroEconomy,
) -> None:
    grid = as_derivation_canvas(ASDerivation(economy, (0.8, 1.2)))
    labor = grid.placements[0].canvas.snapshot().layers
    demands = {
        layer.id: layer
        for layer in labor
        if layer.id
        in {
            "macro.panels.labor.labor_demand.0",
            "macro.panels.labor.labor_demand.1",
        }
    }

    primary = demands["macro.panels.labor.labor_demand.0"]
    shifted = demands["macro.panels.labor.labor_demand.1"]
    assert primary.path[0][0] < shifted.path[0][0]  # type: ignore[attr-defined]
    markers = {layer.id: layer.points[0] for layer in labor if isinstance(layer, MarkerLayer)}
    labels = {
        layer.id.removesuffix(".label"): layer
        for layer in labor
        if isinstance(layer, TextLayer) and ".point." in layer.id
    }
    assert labels
    assert all(label.position == markers[layer_id] for layer_id, label in labels.items())
    assert all(label.offset == (0.0, 7.0) for label in labels.values())

    production = next(
        layer
        for layer in grid.placements[2].canvas.snapshot().layers
        if layer.id == "macro.panels.production.production.0"
    )
    assert production.path[0] == (0.0, 0.0)  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    ("build", "message"),
    (
        (lambda goods, money, economy: ISDerivation(goods, 4.0, (2.0, 2.0)), "distinct"),
        (lambda goods, money, economy: LMDerivation(money, (20.0,)), "at least two"),
        (
            lambda goods, money, economy: ADDerivation(
                ISLM(40.0, 4.0, 10.0, 0.5, 2.0), 20.0, (1.0, -2.0)
            ),
            "positive",
        ),
        (lambda goods, money, economy: ASDerivation(economy, (1.0, 1.0)), "distinct"),
    ),
)
def test_mismatched_sweep_inputs_are_rejected(
    build: object, message: str, goods: KeynesianCross, money: MoneyMarket, economy: MacroEconomy
) -> None:
    with pytest.raises(ValidationError, match=message):
        build(goods, money, economy)  # type: ignore[operator]


def _markers(grid: CanvasGrid) -> list[tuple[float, float]]:
    return [
        point
        for placement in grid.placements
        for layer in placement.canvas.snapshot().layers
        if isinstance(layer, MarkerLayer)
        for point in layer.points
    ]


@pytest.mark.parametrize("kind", ("is", "lm", "ad", "as"))
def test_projection_endpoints_are_solved_markers(
    kind: str, goods: KeynesianCross, money: MoneyMarket, economy: MacroEconomy
) -> None:
    figures = {
        "is": is_derivation_canvas(ISDerivation(goods, 4.0, (2.0, 6.0))),
        "lm": lm_derivation_canvas(LMDerivation(money, (20.0, 25.0))),
        "ad": ad_derivation_canvas(ADDerivation(ISLM(40.0, 4.0, 10.0, 0.5, 2.0), 20.0, (1.0, 2.0))),
        "as": as_derivation_canvas(ASDerivation(economy, (0.8, 1.0, 1.2))),
    }
    grid = figures[kind]
    if kind == "as":
        # the standard four-panel layout carries values by projection paths, not grid links
        assert len(grid.placements) == 4
        return
    markers = _markers(grid)

    assert grid.links
    solved_links = [link for link in grid.links if link.start in markers and link.end in markers]
    assert len(solved_links) >= 2


def test_every_derivation_renders(
    goods: KeynesianCross, money: MoneyMarket, economy: MacroEconomy
) -> None:
    figures = (
        is_derivation_canvas(ISDerivation(goods, 4.0, (2.0, 6.0))),
        lm_derivation_canvas(LMDerivation(money, (20.0, 25.0))),
        ad_derivation_canvas(ADDerivation(ISLM(40.0, 4.0, 10.0, 0.5, 2.0), 20.0, (1.0, 2.0))),
        as_derivation_canvas(ASDerivation(economy, (0.8, 1.0, 1.2))),
    )
    for figure in figures:
        result = figure.render()
        result.close()


def test_title_is_forwarded_to_the_first_panel(goods: KeynesianCross) -> None:
    derivation = ISDerivation(goods, 4.0, (2.0, 6.0))

    untitled = is_derivation_canvas(derivation)
    titled = is_derivation_canvas(derivation, title="Derivation")

    assert untitled.placements[0].canvas.spec.title is None
    assert titled.placements[0].canvas.spec.title == "Derivation"


def test_is_derivation_has_three_fixed_panels_and_extended_curves(
    goods: KeynesianCross,
) -> None:
    derivation = ISDerivation(goods, 4.0, (2.0, 6.0))
    grid = is_derivation_canvas(derivation)

    assert (grid.rows, grid.cols, len(grid.placements)) == (2, 2, 3)
    assert {(item.row, item.col) for item in grid.placements} == {(0, 0), (1, 0), (1, 1)}
    for cell, layer_id, solved in (
        (1, "macro.transmission.is.curve", [state.output for state in derivation.states]),
        (
            2,
            "macro.transmission.is.investment",
            [state.investment for state in derivation.states],
        ),
    ):
        layer = next(
            layer
            for layer in grid.placements[cell].canvas.snapshot().layers
            if layer.id == layer_id
        )
        assert min(point[0] for point in layer.path) < min(solved)  # type: ignore[attr-defined]
        assert max(point[0] for point in layer.path) > max(solved)  # type: ignore[attr-defined]


def test_is_and_investment_curves_have_the_same_screen_slope(
    goods: KeynesianCross,
) -> None:
    grid = is_derivation_canvas(ISDerivation(goods, 4.0, (2.0, 6.0)))

    slopes = []
    for cell, layer_id in (
        (1, "macro.transmission.is.curve"),
        (2, "macro.transmission.is.investment"),
    ):
        canvas = grid.placements[cell].canvas
        layer = next(item for item in canvas.snapshot().layers if item.id == layer_id)
        (x0, y0), (x1, y1) = layer.path  # type: ignore[attr-defined]
        x_span = canvas.spec.x_range[1] - canvas.spec.x_range[0]
        y_span = canvas.spec.y_range[1] - canvas.spec.y_range[0]
        slopes.append(abs((y1 - y0) / y_span) / abs((x1 - x0) / x_span))

    assert slopes[0] == pytest.approx(slopes[1])


def test_is_derivation_emphasizes_the_high_rate_state_and_names_it_a(
    goods: KeynesianCross,
) -> None:
    grid = is_derivation_canvas(ISDerivation(goods, 4.0, (2.0, 6.0)))
    goods_layers = grid.placements[0].canvas.snapshot().layers

    schedules = {
        layer.id: layer.role
        for layer in goods_layers
        if layer.id in {"macro.transmission.is.goods.0", "macro.transmission.is.goods.1"}
    }
    assert schedules == {
        "macro.transmission.is.goods.0": "macro.curve.primary",
        "macro.transmission.is.goods.1": "macro.curve.panel",
    }
    for placement in grid.placements:
        labels = {
            layer.id: layer.text
            for layer in placement.canvas.snapshot().layers
            if isinstance(layer, PointLabelLayer) and ".equilibrium." in layer.id
        }
        assert labels
        assert labels[next(name for name in labels if name.endswith(".0.label"))] == "$B$"
        assert labels[next(name for name in labels if name.endswith(".1.label"))] == "$A$"


def test_ad_derivation_keeps_p0_as_a_and_follows_the_state_change() -> None:
    grid = ad_derivation_canvas(ADDerivation(ISLM(40.0, 4.0, 10.0, 0.5, 2.0), 20.0, (2.0, 1.0)))
    top_layers = grid.placements[0].canvas.snapshot().layers
    lm_roles = {
        layer.id: layer.role
        for layer in top_layers
        if layer.id in {"macro.transmission.ad.lm.0", "macro.transmission.ad.lm.1"}
    }

    assert lm_roles == {
        "macro.transmission.ad.lm.0": "macro.curve.secondary",
        "macro.transmission.ad.lm.1": "macro.curve.secondary.shifted",
    }
    arrow = next(
        layer
        for layer in top_layers
        if isinstance(layer, ArrowLayer) and layer.id == "macro.transmission.ad.lm.shift"
    )
    assert arrow.start[0] < arrow.end[0]
    assert all(placement.canvas.spec.height == 4.5 for placement in grid.placements)
    for placement in grid.placements:
        labels = {
            layer.id: layer.text
            for layer in placement.canvas.snapshot().layers
            if isinstance(layer, PointLabelLayer) and ".equilibrium." in layer.id
        }
        assert labels[next(name for name in labels if name.endswith(".0.label"))] == "$A$"
        assert labels[next(name for name in labels if name.endswith(".1.label"))] == "$B$"


def _panel(grid: CanvasGrid, index: int) -> tuple[object, list[tuple[float, float]]]:
    """The spec of panel ``index`` and its marker points."""
    canvas = grid.placements[index].canvas
    snapshot = canvas.snapshot()
    points = [
        p for layer in snapshot.layers if isinstance(layer, MarkerLayer) for p in layer.points
    ]
    return canvas.spec, points


def test_as_solved_points_sit_at_the_centre_of_their_panels(economy: MacroEconomy) -> None:
    grid = as_derivation_canvas(ASDerivation(economy, (0.8, 1.2)))

    for index in (0, 1):
        spec, points = _panel(grid, index)
        (x0, x1), (y0, y1) = spec.x_range, spec.y_range  # type: ignore[attr-defined]
        centre = (sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points))
        assert centre == pytest.approx(((x0 + x1) / 2, (y0 + y1) / 2), rel=0.05)


def test_as_lines_are_gentle_on_screen(economy: MacroEconomy) -> None:
    grid = as_derivation_canvas(ASDerivation(economy, (0.8, 1.2)))
    spec, points = _panel(grid, 1)
    (x0, x1), (y0, y1) = spec.x_range, spec.y_range  # type: ignore[attr-defined]
    aspect = (y1 - y0) / (x1 - x0)
    (ax, ay), (bx, by) = sorted(points)
    screen = abs((by - ay) / (bx - ax)) / aspect * _panel_ratio(grid)

    assert screen == pytest.approx(AS_SRAS_DISPLAY_SLOPE, rel=0.05)


def _panel_ratio(grid: CanvasGrid) -> float:
    """Height over width of the (square, 45-degree) output panel in data units."""
    spec = grid.placements[3].canvas.spec
    (x0, x1), (y0, y1) = spec.x_range, spec.y_range
    return float((y1 - y0) / (x1 - x0))
