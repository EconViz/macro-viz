"""National-account visual builders using public MosaicKit layers."""

from __future__ import annotations

from mosaickit import AxisMarkLayer, Canvas, CanvasGrid, FillLayer, PathLayer, TextLayer
from mosaickit.styles.nudge import Nudge

from macro_viz.accounts.models import (
    GDPDecompositionResult,
    GDPSeriesResult,
    InflationResult,
    LaborMarketResult,
)
from macro_viz.errors import ValidationError
from macro_viz.series import TimeSeries
from macro_viz.visuals._kit import axes_layers, canvas_spec, new_canvas, title_layer
from macro_viz.visuals._series import SERIES_HEIGHT, SERIES_WIDTH, dated_series_canvas

BAR_HALF_WIDTH = 0.32
"""Half the width of a waterfall bar, in category units."""

HEADROOM_SHARE = 0.1
"""Share of the waterfall's height left above its highest level, for the arrow tip."""

INSIDE_LABEL_SHARE = 0.08
"""A waterfall bar shorter than this share of the axis gets its value outside the bar."""

OUTSIDE_LABEL_GAP = 4.0
"""Gap in points between a short bar and its value."""


def gdp_decomposition_canvas(
    result: GDPDecompositionResult,
    *,
    title: str | None = None,
    y_label: str | None = None,
    width: float = SERIES_WIDTH,
    height: float = SERIES_HEIGHT,
) -> Canvas:
    """Draw the expenditure identity as a waterfall ending at total GDP.

    Values are written on the bars, so the value axis carries no marks. ``y_label`` defaults
    to the unit of the components.
    """
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
    y_range = (low, high + (high - low) * HEADROOM_SHARE)
    last = len(components) + 1
    x_range = (0.0, last + 0.6)
    canvas = new_canvas(canvas_spec(x_range, y_range, width=width, height=height, title=None))
    canvas.extend(
        axes_layers(x_range, y_range, x_label=None, y_label=c.unit if y_label is None else y_label)
    )
    if title:
        canvas.add(title_layer(x_range, y_range, title, above_label=True))
    span = y_range[1] - y_range[0]
    running = 0.0
    for index, (name, symbol, value, role) in enumerate(components, start=1):
        next_level = running + value
        bottom, top = sorted((running, next_level))
        canvas.add(
            FillLayer(
                (
                    (index - BAR_HALF_WIDTH, bottom),
                    (index + BAR_HALF_WIDTH, bottom),
                    (index + BAR_HALF_WIDTH, top),
                    (index - BAR_HALF_WIDTH, top),
                ),
                id=f"macro.accounts.gdp.component.{name}",
                role=role,
            )
        )
        short = abs(value) < INSIDE_LABEL_SHARE * span
        canvas.add(
            TextLayer(
                (index, top if short else (bottom + top) / 2),
                f"{value:g}",
                id=f"macro.accounts.gdp.component.{name}.label",
                role="macro.mark",
                anchor="bottom" if short else "center",
                nudge=Nudge(dy=OUTSIDE_LABEL_GAP) if short else None,
            )
        )
        canvas.add(
            AxisMarkLayer(
                "x", index, symbol, math=True, id=f"macro.accounts.gdp.axis.{name}", role="axes"
            )
        )
        if index < len(components):
            canvas.add(
                PathLayer(
                    (
                        (index + BAR_HALF_WIDTH, next_level),
                        (index + 1 - BAR_HALF_WIDTH, next_level),
                    ),
                    id=f"macro.accounts.gdp.guide.{name}",
                    role="macro.guide",
                )
            )
        running = next_level
    canvas.add(
        FillLayer(
            (
                (last - BAR_HALF_WIDTH, 0),
                (last + BAR_HALF_WIDTH, 0),
                (last + BAR_HALF_WIDTH, result.total),
                (last - BAR_HALF_WIDTH, result.total),
            ),
            id="macro.accounts.gdp.total",
            role="macro.accounts.component.total",
        )
    )
    canvas.add(
        TextLayer(
            (last, result.total / 2),
            f"{result.total:g}",
            id="macro.accounts.gdp.total.label",
            role="macro.mark",
        )
    )
    canvas.add(
        AxisMarkLayer("x", last, "Y", math=True, id="macro.accounts.gdp.axis.total", role="axes")
    )
    return canvas


def gdp_levels_canvas(
    result: GDPSeriesResult, *, title: str | None = None, **options: object
) -> Canvas:
    """Draw aligned nominal and real GDP levels, which share a unit and a magnitude."""
    return dated_series_canvas(
        (
            (result.nominal, "macro.accounts.gdp.nominal", "macro.series.primary"),
            (result.real, "macro.accounts.gdp.real", "macro.series.secondary"),
        ),
        title=title,
        **options,  # type: ignore[arg-type]
    )


def gdp_deflator_canvas(
    result: GDPSeriesResult, *, title: str | None = None, **options: object
) -> Canvas:
    """Draw the GDP deflator while retaining its base metadata in the result."""
    return price_index_canvas(result.deflator, title=title, **options)


def price_index_canvas(
    price_index: TimeSeries, *, title: str | None = None, **options: object
) -> Canvas:
    """Draw CPI or another explicitly based price index."""
    if price_index.index_base is None:
        raise ValidationError("price-index figures require index-base metadata")
    return dated_series_canvas(
        ((price_index, "macro.accounts.price.index", "macro.series.secondary"),),
        title=title,
        **options,  # type: ignore[arg-type]
    )


def inflation_canvas(
    result: InflationResult, *, title: str | None = None, **options: object
) -> Canvas:
    """Draw the inflation rate derived from a price index, with a zero line when it crosses."""
    return dated_series_canvas(
        ((result.inflation_rate, "macro.accounts.inflation.rate", "macro.series.secondary"),),
        title=title,
        **options,  # type: ignore[arg-type]
    )


def labor_market_canvas(
    result: LaborMarketResult,
    *,
    title: str | None = None,
    width: float = SERIES_WIDTH,
    height: float = SERIES_HEIGHT,
    **options: object,
) -> CanvasGrid:
    """Draw employment above unemployment, each with its own axis.

    The two levels differ by an order of magnitude, so they never share an axis: two stacked
    panels share only the dates. ``title`` heads the upper panel; ``height`` is the height
    of each panel.
    """
    upper = dated_series_canvas(
        ((result.employment, "macro.accounts.labor.employment", "macro.series.secondary"),),
        title=title,
        show_dates=False,
        width=width,
        height=height,
        **options,  # type: ignore[arg-type]
    )
    lower = dated_series_canvas(
        ((result.unemployment, "macro.accounts.labor.unemployment", "macro.series.primary"),),
        title=None,
        include_zero=True,
        width=width,
        height=height,
        **options,  # type: ignore[arg-type]
    )
    return CanvasGrid([[upper], [lower]])


def unemployment_rate_canvas(
    result: LaborMarketResult, *, title: str | None = None, **options: object
) -> Canvas:
    """Draw unemployment as a percentage of the labour force."""
    options.setdefault("include_zero", True)
    return dated_series_canvas(
        (
            (
                result.unemployment_rate,
                "macro.accounts.labor.unemployment.rate",
                "macro.series.secondary",
            ),
        ),
        title=title,
        **options,  # type: ignore[arg-type]
    )
