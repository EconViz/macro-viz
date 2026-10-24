"""Render employment, unemployment, and the unemployment rate."""

from __future__ import annotations

from datetime import date

from common import prepare_manual_output

from macro_viz import TimeSeries
from macro_viz.accounts import analyze_labor_market
from macro_viz.visuals import labor_market_canvas, unemployment_rate_canvas


def main() -> None:
    output = prepare_manual_output()
    dates = tuple(date(year, 1, 1) for year in range(2019, 2025))
    labor_force = TimeSeries(
        "Labor force", dates, (165, 166, 167, 169, 171, 173), "millions of people"
    )
    employment = TimeSeries(
        "Employment", dates, (158, 157, 159, 162, 165, 168), "millions of people"
    )
    result = analyze_labor_market(labor_force, employment)

    labor_market_canvas(result, title="Employment and unemployment").save(
        output / "labor_market.png"
    )
    unemployment_rate_canvas(result, title="Unemployment rate").save(
        output / "unemployment_rate.png"
    )


if __name__ == "__main__":
    main()
