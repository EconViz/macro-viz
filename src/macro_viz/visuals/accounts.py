"""National-account visual builders using public MosaicKit layers."""

from __future__ import annotations

from mosaickit import (
    AxisMarkLayer,
    AxisSpec,
    Canvas,
    CanvasSpec,
    FillLayer,
    PathLayer,
    TextLayer,
    build_axes,
)
from mosaickit.styles.nudge import Nudge

from macro_viz.accounts.models import (
    GDPDecompositionResult,
    GDPSeriesResult,
    InflationResult,
    LaborMarketResult,
)
from macro_viz.errors import ValidationError
from macro_viz.series import TimeSeries
from macro_viz.visuals._common import dated_series_canvas, new_canvas, value_mark_layers


def gdp_decomposition_canvas(result: GDPDecompositionResult, *, title: str | None = None) -> Canvas:
    """Draw the expenditure identity as a waterfall ending at total GDP."""
    c = result.components
    components = (
        ("consumption", "C", c.consumption, "macro.accounts.component.consumption"),
        ("investment", "I", c.investment, "macro.accounts.component.investment"),
        ("government", "G", c.government, "macro.accounts.component.government"),
        ("net_exports", "NX", c.net_exports, "macro.accounts.component.net.exports"),
    )
    levels = [0.0]
    for _, _, value, _ in components:
        levels.append(levels[-1] + value)
    low, high = min(0.0, *levels), max(0.0, *levels)
    padding = max((high - low) * 0.1, 1.0)
    x_range, y_range = (0.4, 5.6), (low - padding, high + padding)
    canvas = new_canvas(
        CanvasSpec(
            x_range=x_range,
            y_range=y_range,
            width=7.0,
            height=4.8,
            x_label="Component",
            y_label=c.unit,
            title=title,
        )
    )
    canvas.extend(build_axes(AxisSpec(x_range), AxisSpec(y_range)))
    canvas.extend(value_mark_layers(y_range))
    running = 0.0
    for index, (name, symbol, value, role) in enumerate(components, start=1):
        next_level = running + value
        bottom, top = sorted((running, next_level))
        canvas.add(
            FillLayer(
                (
                    (index - 0.32, bottom),
                    (index + 0.32, bottom),
                    (index + 0.32, top),
                    (index - 0.32, top),
                ),
                id=f"macro.accounts.gdp.component.{name}",
                role=role,
            )
        )
        label_position = (index, (bottom + top) / 2)
        label_anchor = "center"
        label_nudge = None
        if value < 0:
            label_position = (index, next_level)
            label_anchor = "top"
            label_nudge = Nudge(dy=-7)
        canvas.add(
            TextLayer(
                label_position,
                f"{value:g}",
                id=f"macro.accounts.gdp.component.{name}.label",
                role=role,
                anchor=label_anchor,
                nudge=label_nudge,
            )
        )
        canvas.add(
            AxisMarkLayer(
                "x",
                index,
                symbol,
                math=True,
                id=f"macro.accounts.gdp.axis.{name}",
                role="axes",
            )
        )
        if index < len(components):
            canvas.add(
                PathLayer(
                    ((index + 0.32, next_level), (index + 0.68, next_level)),
                    id=f"macro.accounts.gdp.guide.{name}",
                    role="macro.guide",
                )
            )
        running = next_level
    canvas.add(
        FillLayer(
            ((4.68, 0), (5.32, 0), (5.32, result.total), (4.68, result.total)),
            id="macro.accounts.gdp.total",
            role="macro.accounts.component.total",
        )
    )
    canvas.add(
        TextLayer(
            (5, result.total / 2),
            f"{result.total:g}",
            id="macro.accounts.gdp.total.label",
            role="macro.accounts.component.total",
        )
    )
    canvas.add(
        AxisMarkLayer("x", 5, "Y", math=True, id="macro.accounts.gdp.axis.total", role="axes")
    )
    return canvas


def gdp_levels_canvas(result: GDPSeriesResult, *, title: str | None = None) -> Canvas:
    """Draw aligned nominal and real GDP levels."""
    return dated_series_canvas(
        (
            (result.nominal, "macro.accounts.gdp.nominal", "macro.series.primary", "Nominal GDP"),
            (result.real, "macro.accounts.gdp.real", "macro.series.secondary", "Real GDP"),
        ),
        title=title,
    )


def gdp_deflator_canvas(result: GDPSeriesResult, *, title: str | None = None) -> Canvas:
    """Draw the GDP deflator while retaining its base metadata in the result."""
    return price_index_canvas(result.deflator, title=title)


def price_index_canvas(price_index: TimeSeries, *, title: str | None = None) -> Canvas:
    """Draw CPI or another explicitly based price index."""
    if price_index.index_base is None:
        raise ValidationError("price-index figures require index-base metadata")
    return dated_series_canvas(
        ((price_index, "macro.accounts.price.index", "macro.series.primary", price_index.name),),
        title=title,
    )


def inflation_canvas(result: InflationResult, *, title: str | None = None) -> Canvas:
    """Draw the inflation rate derived from a price index."""
    return dated_series_canvas(
        (
            (
                result.inflation_rate,
                "macro.accounts.inflation.rate",
                "macro.series.accent",
                "Inflation",
            ),
        ),
        title=title,
        include_zero=True,
    )


def labor_market_canvas(result: LaborMarketResult, *, title: str | None = None) -> Canvas:
    """Draw employment and unemployment levels in their common unit."""
    return dated_series_canvas(
        (
            (
                result.employment,
                "macro.accounts.labor.employment",
                "macro.series.primary",
                "Employment",
            ),
            (
                result.unemployment,
                "macro.accounts.labor.unemployment",
                "macro.series.accent",
                "Unemployment",
            ),
        ),
        title=title,
        include_zero=True,
    )


def unemployment_rate_canvas(result: LaborMarketResult, *, title: str | None = None) -> Canvas:
    """Draw unemployment as a percentage of the labour force."""
    return dated_series_canvas(
        (
            (
                result.unemployment_rate,
                "macro.accounts.labor.unemployment.rate",
                "macro.series.accent",
                "Unemployment rate",
            ),
        ),
        title=title,
        include_zero=True,
    )
