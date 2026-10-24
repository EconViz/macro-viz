from __future__ import annotations

from datetime import date
from pathlib import Path

from mosaickit import FillLayer, MarkerLayer, PathLayer, TextLayer

from macro_viz import IndexBase, TimeSeries
from macro_viz.accounts import (
    GDPComponents,
    analyze_gdp_components,
    analyze_gdp_series,
    analyze_labor_market,
    calculate_inflation,
)
from macro_viz.cycles import RecessionPeriod, analyze_business_cycle
from macro_viz.visuals import (
    business_cycle_canvas,
    gdp_decomposition_canvas,
    gdp_deflator_canvas,
    gdp_levels_canvas,
    inflation_canvas,
    labor_market_canvas,
    output_gap_canvas,
    price_index_canvas,
    unemployment_rate_canvas,
)

DATES = tuple(date(year, 1, 1) for year in range(2018, 2025))


def series(
    name: str,
    values: tuple[float | None, ...],
    unit: str = "billions",
    index_base: IndexBase | None = None,
) -> TimeSeries:
    return TimeSeries(name, DATES, values, unit, index_base)


def layer_ids(canvas: object) -> set[str]:
    return {layer.id for layer in canvas.snapshot().layers}  # type: ignore[attr-defined]


def test_gdp_decomposition_has_stable_namespaced_ids_and_optional_title() -> None:
    result = analyze_gdp_components(GDPComponents(60, 20, 25, -5, "billions"))

    untitled = gdp_decomposition_canvas(result)
    titled = gdp_decomposition_canvas(result, title="GDP components")

    assert untitled.spec.title is None
    assert titled.spec.title == "GDP components"
    assert {
        "macro.accounts.gdp.component.consumption",
        "macro.accounts.gdp.component.investment",
        "macro.accounts.gdp.component.government",
        "macro.accounts.gdp.component.net_exports",
        "macro.accounts.gdp.total",
    } <= layer_ids(untitled)
    assert all(
        layer.id == "axes.frame" or layer.id.startswith("macro.")
        for layer in untitled.snapshot().layers
    )
    assert "macro.axis.value.0" in layer_ids(untitled)
    net_exports_label = next(
        layer
        for layer in untitled.snapshot().layers
        if layer.id == "macro.accounts.gdp.component.net_exports.label"
    )
    assert isinstance(net_exports_label, TextLayer)
    assert net_exports_label.nudge is not None
    assert net_exports_label.nudge.dy < 0


def test_account_series_visuals_expose_each_economic_series() -> None:
    nominal = series("Nominal GDP", (100, 105, 110, 115, 120, 125, 130))
    real = series("Real GDP", (100, 103, 106, 108, 110, 112, 115))
    gdp = analyze_gdp_series(nominal, real, base_period=DATES[0])
    cpi = series("CPI", (100, 102, 105, 108, 111, 115, 118), "index", IndexBase(DATES[0]))
    inflation = calculate_inflation(cpi)
    labor = analyze_labor_market(
        series("Labor force", (100, 101, 102, 103, 104, 105, 106), "millions"),
        series("Employment", (95, 96, 97, 98, 99, 100, 101), "millions"),
    )

    assert {
        "macro.accounts.gdp.nominal",
        "macro.accounts.gdp.real",
    } <= layer_ids(gdp_levels_canvas(gdp))
    assert "macro.axis.value.0" in layer_ids(gdp_levels_canvas(gdp))
    assert "macro.accounts.price.index" in layer_ids(gdp_deflator_canvas(gdp))
    assert "macro.accounts.price.index" in layer_ids(price_index_canvas(cpi))
    assert "macro.accounts.inflation.rate" in layer_ids(inflation_canvas(inflation))
    assert {
        "macro.accounts.labor.employment",
        "macro.accounts.labor.unemployment",
    } <= layer_ids(labor_market_canvas(labor))
    assert "macro.accounts.labor.unemployment.rate" in layer_ids(unemployment_rate_canvas(labor))


def test_business_cycle_visual_has_recession_turning_and_gap_layers() -> None:
    actual = series("Real GDP", (100, 110, 105, 115, 108, 112, 120))
    trend = series("Potential GDP", (100, 105, 107, 110, 112, 115, 118))
    result = analyze_business_cycle(
        actual,
        trend=trend,
        recessions=(RecessionPeriod(DATES[2], DATES[4]),),
    )

    cycle = business_cycle_canvas(result, title="Business cycle")
    gap = output_gap_canvas(result)

    assert cycle.spec.title == "Business cycle"
    assert {
        "macro.cycles.output",
        "macro.cycles.trend",
        "macro.cycles.recession.0",
        "macro.cycles.peak.0",
        "macro.cycles.trough.0",
    } <= layer_ids(cycle)
    output_label = next(
        layer for layer in cycle.snapshot().layers if layer.id == "macro.cycles.output.label"
    )
    trend_label = next(
        layer for layer in cycle.snapshot().layers if layer.id == "macro.cycles.trend.label"
    )
    assert isinstance(output_label, TextLayer)
    assert isinstance(trend_label, TextLayer)
    assert output_label.nudge is not None
    assert trend_label.nudge is not None
    assert trend_label.nudge.dy < 0 < output_label.nudge.dy
    assert isinstance(
        next(layer for layer in cycle.snapshot().layers if layer.id == "macro.cycles.recession.0"),
        FillLayer,
    )
    assert isinstance(
        next(layer for layer in cycle.snapshot().layers if layer.id == "macro.cycles.peak.0"),
        MarkerLayer,
    )
    assert {
        "macro.cycles.output.gap.positive.1",
        "macro.cycles.output.gap.negative.2",
        "macro.cycles.output.gap.zero",
    } <= layer_ids(gap)


def test_missing_values_split_paths_instead_of_connecting_across_gaps() -> None:
    actual = series("Real GDP", (100, 101, None, 103, 104, 105, 106))
    trend = series("Potential GDP", (100, 101, 102, 103, 104, 105, 106))

    canvas = business_cycle_canvas(analyze_business_cycle(actual, trend=trend))
    output_paths = [
        layer
        for layer in canvas.snapshot().layers
        if isinstance(layer, PathLayer) and layer.id.startswith("macro.cycles.output.segment")
    ]

    assert [layer.id for layer in output_paths] == [
        "macro.cycles.output.segment.0",
        "macro.cycles.output.segment.1",
    ]
    assert output_paths[0].path == ((0.0, 100.0), (1.0, 101.0))
    assert output_paths[1].path[0] == (3.0, 103.0)


def test_canvas_renders_and_saves_through_mosaickit(tmp_path: Path) -> None:
    result = analyze_gdp_components(GDPComponents(60, 20, 25, -5, "billions"))
    canvas = gdp_decomposition_canvas(result)

    png = tmp_path / "gdp.png"
    rendered = canvas.render()
    try:
        canvas.save(png)
    finally:
        rendered.close()

    assert png.stat().st_size > 0
