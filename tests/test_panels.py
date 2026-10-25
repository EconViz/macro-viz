"""Linked panels: solved blocks agree, panels align exactly, and nothing is hard-coded."""

from __future__ import annotations

import re
import warnings
from collections.abc import Iterator
from pathlib import Path

import pytest
from mosaickit import CanvasGrid, PathLayer

from macro_viz import Config, ValidationError
from macro_viz.panels import (
    Hop,
    IsLm,
    IsLmSketch,
    LinearFunction,
    MacroEconomy,
    PanelLayout,
    PanelSpec,
    QuadraticProduction,
    Scenario,
    Shock,
    Step,
    five_panel_layout,
    four_panel_layout,
)
from macro_viz.panels.model import N, P, R, W, Y
from macro_viz.visuals import five_panel_canvas, four_panel_canvas, linked_panels_canvas


@pytest.fixture(autouse=True)
def _reset_config() -> Iterator[None]:
    yield
    Config.reset()


def economy(islm: bool = False) -> MacroEconomy:
    block = IsLm(0.0, 1.0, 4.0, 0.4, 0.2) if islm else None
    base = MacroEconomy(
        QuadraticProduction(3.0, 0.2, 1.0), LinearFunction(0.4, 0.25), 1.0, 1.0, block
    )
    return base.calibrated(2.0) if islm else base


def capital_scenario(price_after: float = 0.8) -> Scenario:
    shock = Shock(capital=1.5)
    return Scenario(
        economy(),
        (
            Step("A", price=1.0),
            Step("B", shock, price=1.0),
            Step("C", shock, price=price_after),
        ),
        IsLmSketch(("A", "C"), 2.0, -0.07, 0.14),
    )


def derived_scenario() -> Scenario:
    base = economy(islm=True)
    assert base.islm is not None
    shock = Shock(expenditure=1.12 * base.islm.expenditure)
    return Scenario(base, (Step("A"), Step("B", shock), Step("C", shock, adjust_expectations=True)))


# -- models -----------------------------------------------------------------------------


def test_capital_scenario_keeps_the_lecture_order() -> None:
    a, b, c = (state.values for state in capital_scenario().solve())

    assert a[N] < c[N] < b[N]
    assert a[Y] < c[Y] < b[Y]
    assert a[W] < c[W]
    assert c[P] < a[P]
    assert c[R] < a[R]
    assert R not in b


def test_one_output_in_production_ad_as_and_is_lm() -> None:
    for state in derived_scenario().solve():
        islm = state.economy.islm
        assert islm is not None
        output = state.values[Y]
        assert state.economy.production.output(state.values[N], state.economy.capital) == output
        if state.clearing:
            price = state.values[P]
            assert islm.demand_output(price) == pytest.approx(output)
            assert islm.is_rate(output) == pytest.approx(state.values[R])
            assert islm.lm_rate(output, price) == pytest.approx(state.values[R])


def test_expectations_catch_up_to_natural_output() -> None:
    a, b, c = derived_scenario().solve()

    assert b.values[Y] > a.values[Y]
    assert c.values[Y] == pytest.approx(c.economy.natural_output)
    assert c.values[P] > b.values[P] > a.values[P]


def test_labor_market_clears_and_supply_responds_to_price() -> None:
    eco = economy()
    n = eco.employment(1.0)

    assert eco.labor_demand(n, 1.0) == pytest.approx(eco.labor_supply_wage(n))
    assert eco.output(1.5) > eco.output(1.0)
    assert eco.output(1.5, expected_price=1.5) == pytest.approx(eco.output(1.0, 1.0))


def test_a_shock_to_money_needs_an_islm_block() -> None:
    with pytest.raises(ValidationError):
        Shock(money=2.0).apply(economy())


# -- layout -----------------------------------------------------------------------------


def test_layout_rejects_overlap_and_unshared_axes() -> None:
    panels = (PanelSpec("a", "labor", N, W, 0, 0), PanelSpec("b", "adas", Y, P, 0, 0))
    with pytest.raises(ValidationError):
        PanelLayout(panels, (), ())
    from macro_viz.panels import Projection

    misaligned = (
        PanelSpec("a", "labor", N, W, 0, 0),
        PanelSpec("b", "production", N, Y, 1, 1),
    )
    path = Projection("n", ((Hop("a", N, W), Hop("b", N, Y)),))
    with pytest.raises(ValidationError):
        PanelLayout(misaligned, (path,), ())


def test_five_panel_layout_stacks_islm_over_adas() -> None:
    layout = five_panel_layout()

    islm, adas = layout.panel("islm"), layout.panel("adas")
    assert (islm.col, islm.cols) == (adas.col, adas.cols)
    assert islm.row < adas.row
    assert layout.panel("labor").col == 0 and layout.panel("labor").row >= islm.rows


# -- alignment --------------------------------------------------------------------------


def _pixels(grid: object, cell: int, point: tuple[float, float]) -> tuple[float, float]:
    result = grid.render()  # type: ignore[attr-defined]
    ax = result.axes[cell]
    x, y = ax.transData.transform(point)
    result.close()
    return float(x), float(y)


def test_links_end_on_the_same_pixel_column_or_row() -> None:
    grid = five_panel_canvas(capital_scenario())
    result = grid.render()
    try:
        assert grid.links
        for link in grid.links:
            sx, sy = result.axes[link.start_cell].transData.transform(link.start)
            ex, ey = result.axes[link.end_cell].transData.transform(link.end)
            assert abs(sx - ex) < 0.5 or abs(sy - ey) < 0.5
    finally:
        result.close()


def test_panels_sharing_a_variable_share_its_pixels() -> None:
    grid = five_panel_canvas(capital_scenario())
    result = grid.render()
    try:
        layout = five_panel_layout()
        order = sorted(layout.panels, key=lambda panel: (panel.row, panel.col))
        axes = {panel.key: result.axes[i] for i, panel in enumerate(order)}
        value = 7.0
        columns = {key: axes[key].transData.transform((value, 0.0))[0] for key in ("islm", "adas")}
        assert abs(columns["islm"] - columns["adas"]) < 0.5
        diagonal = axes["diagonal"].transData.transform((value, 0.0))[0]
        assert abs(diagonal - columns["adas"]) < 0.5
        labor = axes["labor"].transData.transform((value, 0.0))[0]
        production = axes["production"].transData.transform((value, 0.0))[0]
        assert abs(labor - production) < 0.5
        rows = [axes[k].transData.transform((0.0, value))[1] for k in ("production", "diagonal")]
        assert abs(rows[0] - rows[1]) < 0.5
    finally:
        result.close()


def test_gap_crossings_start_and_end_on_the_dashed_pieces() -> None:
    grid = four_panel_canvas(capital_scenario())

    for link in grid.links:
        start_canvas = grid.placements[link.start_cell].canvas
        end_canvas = grid.placements[link.end_cell].canvas
        pieces = [
            layer
            for canvas in (start_canvas, end_canvas)
            for layer in canvas.snapshot().layers
            if isinstance(layer, PathLayer) and layer.role == "macro.link"
        ]
        points = {tuple(round(v, 9) for v in point) for layer in pieces for point in layer.path}
        assert tuple(round(v, 9) for v in link.start) in points
        assert tuple(round(v, 9) for v in link.end) in points


def test_projection_reads_the_solved_values() -> None:
    scenario = capital_scenario()
    grid = four_panel_canvas(scenario)
    a = scenario.solve()[0].values
    labor = next(p.canvas for p in grid.placements if p.row == 0 and p.col == 0)
    ids = {layer.id: layer for layer in labor.snapshot().layers}
    marker = ids["macro.panels.labor.point.A"]

    assert marker.points[0] == pytest.approx((a[N], a[W]))  # type: ignore[attr-defined]


# -- parameters and settings ------------------------------------------------------------


def _text(grid: CanvasGrid) -> str:
    return " ".join(repr(layer) for p in grid.placements for layer in p.canvas.snapshot().layers)


def test_title_is_a_parameter() -> None:
    plain = four_panel_canvas(capital_scenario())
    titled = four_panel_canvas(capital_scenario(), title="Linked")

    titles = [p.canvas.spec.title for p in plain.placements]
    assert titles == [None] * len(titles)
    assert [p.canvas.spec.title for p in titled.placements].count("Linked") == 1


def test_economic_parameters_change_the_figure() -> None:
    assert _text(four_panel_canvas(capital_scenario(0.8))) != _text(
        four_panel_canvas(capital_scenario(0.7))
    )


def test_output_is_unchanged_without_settings(tmp_path: Path) -> None:
    first, second = tmp_path / "a.svg", tmp_path / "b.svg"
    four_panel_canvas(capital_scenario()).save(first)
    Config.reset()
    four_panel_canvas(capital_scenario()).save(second)

    def body(path: Path) -> str:
        text = re.sub(r"<dc:date>[^<]*</dc:date>", "", path.read_text("utf-8"))
        return re.sub(r"\b[a-z][0-9a-f]{10}\b", "id", text)

    assert body(first) == body(second)


def test_labels_come_from_the_locale_table_and_can_be_overridden() -> None:
    plain = _text(five_panel_canvas(capital_scenario()))
    named = _text(five_panel_canvas(capital_scenario(), labels={"panels.curve.ad": "$DEMAND$"}))

    assert "DEMAND" not in plain and "DEMAND" in named
    with pytest.raises(ValidationError):
        five_panel_canvas(capital_scenario(), labels={"panels.curve.nothing": "x"})


def test_point_and_curve_labels_have_stable_ids_for_label_overrides() -> None:
    grid = five_panel_canvas(capital_scenario())
    ids = {layer.id for p in grid.placements for layer in p.canvas.snapshot().layers}

    assert {
        "macro.panels.labor.point.A.label",
        "macro.panels.islm.lm.1.label",
        "macro.panels.adas.ad.0.label",
    } <= ids


def test_label_nudges_of_the_settings_move_labels() -> None:
    base = _text(four_panel_canvas(capital_scenario()))
    Config.from_dict({"macro": {"label": {"point": {"top": "4pt"}}}}).use()

    assert _text(four_panel_canvas(capital_scenario())) != base


def test_modes_and_visibility_options_change_what_is_drawn() -> None:
    scenario = derived_scenario()
    schematic = _text(linked_panels_canvas(scenario, four_panel_layout()))
    from macro_viz.panels import Mode

    derived = _text(linked_panels_canvas(scenario, four_panel_layout(), mode=Mode.DERIVED))
    with_lras = _text(linked_panels_canvas(scenario, four_panel_layout(), lras=True))

    assert len({schematic, derived, with_lras}) == 3
    with pytest.raises(ValidationError):
        linked_panels_canvas(scenario, four_panel_layout(), steps=["Z"])


def test_every_preset_renders_without_error(tmp_path: Path) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        five_panel_canvas(derived_scenario(), lras=True).save(tmp_path / "x.svg")
        four_panel_canvas(capital_scenario()).save(tmp_path / "y.svg")

    assert (tmp_path / "x.svg").stat().st_size > 0
    assert (tmp_path / "y.svg").stat().st_size > 0
