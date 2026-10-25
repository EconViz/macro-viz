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
    ArrowOptions,
    Curve,
    CurveOptions,
    Hop,
    IsLm,
    IsLmSketch,
    LinearFunction,
    MacroEconomy,
    MovementKind,
    PanelLayout,
    PanelSpec,
    QuadraticProduction,
    RotationDirection,
    Scenario,
    ShiftDirection,
    Shock,
    Step,
    axis_lengths,
    curve_specs,
    five_panel_layout,
    four_panel_layout,
    shift_arrows,
)
from macro_viz.panels.model import N, P, R, W, Y
from macro_viz.visuals import five_panel_canvas, four_panel_canvas, linked_panels_canvas
from macro_viz.visuals.panels import _rotation_arrows


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


def test_direct_curve_movements_apply_one_schematic_preset_and_solve() -> None:
    base = economy(islm=True)
    movements = (
        base.curve(Curve.PRODUCTION).rotate(RotationDirection.OUTWARD),
        base.curve(Curve.LABOR_DEMAND).rotate(RotationDirection.OUTWARD),
    )
    scenario = Scenario(base, (Step("A"), Step("B", movements=movements)))
    before, after = scenario.solve()

    assert after.economy.capital == pytest.approx(1.5 * before.economy.capital)
    assert after.values[Y] > before.values[Y]
    assert after.economy.labor_demand(after.values[N], after.values[P]) == pytest.approx(
        after.values[W]
    )
    assert scenario.movement_kinds() == {
        "production": MovementKind.ROTATION,
        "labor_demand": MovementKind.ROTATION,
    }


def test_direct_curve_shift_uses_direction_without_policy_inference() -> None:
    base = economy(islm=True)
    assert base.islm is not None
    scenario = Scenario(
        base,
        (Step("A"), Step("B", movements=(base.curve(Curve.LM).shift(ShiftDirection.RIGHT),))),
    )
    before, after = scenario.solve()

    before_islm, after_islm = before.economy.islm, after.economy.islm
    assert before_islm is not None and after_islm is not None
    assert after_islm.money > before_islm.money
    assert after.values[R] < before.values[R]


def test_curve_rejects_an_unsupported_movement_at_the_api_boundary() -> None:
    base = economy(islm=True)

    with pytest.raises(ValidationError, match="does not support a rotation"):
        base.curve(Curve.LM).rotate(RotationDirection.OUTWARD)
    with pytest.raises(ValidationError, match="needs an IS-LM model"):
        economy().curve(Curve.LM)


@pytest.mark.parametrize("label", ("AA", "1", "甲", "A'"))
def test_step_label_is_exactly_one_ascii_letter(label: str) -> None:
    with pytest.raises(ValidationError, match="one ASCII letter"):
        Step(label)


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
    assert {panel.rows for panel in layout.panels} == {3}


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


def test_output_guides_start_at_the_production_function_not_the_y_axis() -> None:
    scenario = capital_scenario()
    grid = five_panel_canvas(scenario)
    production = next(p.canvas for p in grid.placements if p.row == 6 and p.col == 0)
    guides = [
        layer.path
        for layer in production.snapshot().layers
        if isinstance(layer, PathLayer)
        and layer.role == "macro.link"
        and layer.path[0][1] == layer.path[-1][1]
    ]

    for state in scenario.solve():
        matching = [path for path in guides if path[0][1] == pytest.approx(state.values[Y])]
        assert matching
        assert matching[0][0][0] == pytest.approx(state.values[N])


def test_every_translation_arrow_starts_at_an_equilibrium_and_runs_horizontally() -> None:
    scenario = capital_scenario()
    states = scenario.solve()
    layout = five_panel_layout()
    ranges = axis_lengths(states, extent=1.7)
    expected_starts = {
        "islm": [(states[0].values[Y], states[0].values[R])],
        "adas": [(states[0].values[Y], states[0].values[P])],
    }

    for panel_key, starts in expected_starts.items():
        panel = layout.panel(panel_key)
        curves = curve_specs(panel, scenario, states, ranges, CurveOptions())
        arrows = shift_arrows(
            panel,
            curves,
            states,
            dict(ranges.lengths),
            ArrowOptions(),
            scenario.movement_kinds(),
        )
        assert [arrow.points[0] for arrow in arrows] == pytest.approx(starts)
        assert all(len(arrow.points) == 2 for arrow in arrows)
        assert all(arrow.points[0][1] == pytest.approx(arrow.points[1][1]) for arrow in arrows)


def test_rotation_arrows_use_angle_derived_beziers_inside_the_panel() -> None:
    scenario = capital_scenario()
    states = scenario.solve()
    layout = five_panel_layout()
    ranges = axis_lengths(states, extent=1.7)

    for panel_key in ("production",):
        panel = layout.panel(panel_key)
        curves = curve_specs(panel, scenario, states, ranges, CurveOptions())
        arrows = _rotation_arrows(
            panel,
            curves,
            ranges.lengths,
            scenario.movement_kinds(),
            ArrowOptions(),
        )
        for arrow in arrows:
            assert len(arrow.points) == 48
            assert all(
                0 <= x <= ranges.lengths[panel.x] and 0 <= y <= ranges.lengths[panel.y]
                for x, y in arrow.points
            )


def test_labor_rotation_markers_are_separate_and_search_from_the_tail() -> None:
    scenario = capital_scenario()
    states = scenario.solve()
    panel = five_panel_layout().panel("labor")
    ranges = axis_lengths(states, extent=1.7)
    curves = curve_specs(panel, scenario, states, ranges, CurveOptions())
    arrows = _rotation_arrows(
        panel,
        curves,
        ranges.lengths,
        scenario.movement_kinds(),
        ArrowOptions(),
    )

    assert len(arrows) == 2
    first = {(round(x, 5), round(y, 5)) for x, y in arrows[0].points}
    second = {(round(x, 5), round(y, 5)) for x, y in arrows[1].points}
    assert first.isdisjoint(second)


def test_lm_and_as_labels_are_fractional_and_fixed_above_right_of_curve_tails() -> None:
    grid = five_panel_canvas(capital_scenario())
    layers = {
        layer.id: layer
        for placement in grid.placements
        for layer in placement.canvas.snapshot().layers
    }

    for base in (
        "macro.panels.islm.lm.0",
        "macro.panels.islm.lm.1",
        "macro.panels.adas.sras.0",
        "macro.panels.adas.sras.1",
    ):
        curve, label = layers[base], layers[f"{base}.label"]
        tail = max(curve.path, key=lambda point: (point[0], point[1]))  # type: ignore[attr-defined]
        assert label.position[0] > tail[0]  # type: ignore[attr-defined]
        assert label.position[1] > tail[1]  # type: ignore[attr-defined]
        assert f"{base}.label.leader" not in layers

    assert r"\frac{M_0}{p_0}" in str(layers["macro.panels.islm.lm.0.label"].text)  # type: ignore[attr-defined]
    assert r"\frac{M_0}{p_2}" in str(layers["macro.panels.islm.lm.1.label"].text)  # type: ignore[attr-defined]


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


def test_row_and_column_gaps_are_parameters() -> None:
    tight = four_panel_canvas(capital_scenario(), column_gap=0.0, row_gap=0.0)
    loose = four_panel_canvas(capital_scenario(), column_gap=0.4, row_gap=0.4)

    def gap(grid: CanvasGrid) -> float:
        result = grid.render()
        try:
            boxes = [ax.get_position() for ax in result.axes]
            return float(max(b.x0 for b in boxes) - min(b.x1 for b in boxes))
        finally:
            result.close()

    assert gap(tight) < gap(loose)


def test_a_crowded_label_gets_a_leader_instead_of_overlapping() -> None:
    from macro_viz.visuals._placement import PlacementOptions, Scene, place

    options = PlacementOptions()
    scene = Scene(limits=(0.0, 0.0, 200.0, 200.0))
    scene.add_polyline([(0.0, 100.0), (200.0, 100.0)])
    scene.add_polyline([(100.0, 0.0), (100.0, 200.0)])
    scene.boxes.append((105.0, 105.0, 160.0, 130.0))
    crowded = place((100.0, 100.0), (30.0, 18.0), scene, options, ("upper-right", "right"))

    assert crowded.leader is not None
