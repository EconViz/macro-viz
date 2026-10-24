"""Render nominal/real GDP, the deflator, CPI, and inflation."""

from __future__ import annotations

from datetime import date

from common import prepare_manual_output

from macro_viz import IndexBase, TimeSeries
from macro_viz.accounts import analyze_gdp_series, calculate_inflation
from macro_viz.visuals import (
    gdp_deflator_canvas,
    gdp_levels_canvas,
    inflation_canvas,
    price_index_canvas,
)


def main() -> None:
    output = prepare_manual_output()
    dates = tuple(date(year, 1, 1) for year in range(2019, 2025))
    nominal = TimeSeries(
        "Nominal GDP",
        dates,
        (1000, 1040, 1113, 1196, 1275, 1365),
        "billions USD",
    )
    real = TimeSeries(
        "Real GDP",
        dates,
        (1000, 1010, 1060, 1100, 1140, 1180),
        "billions USD",
    )
    gdp = analyze_gdp_series(nominal, real, base_period=dates[0])
    cpi = TimeSeries(
        "CPI",
        dates,
        (100, 102, 105, 109, 113, 116),
        "index",
        IndexBase(dates[0]),
    )
    inflation = calculate_inflation(cpi)

    gdp_levels_canvas(gdp, title="Nominal and real GDP").save(output / "gdp_levels.png")
    gdp_deflator_canvas(gdp, title="GDP deflator").save(output / "gdp_deflator.png")
    price_index_canvas(cpi, title="Consumer price index").save(output / "cpi.png")
    inflation_canvas(inflation, title="CPI inflation").save(output / "inflation.png")


if __name__ == "__main__":
    main()
