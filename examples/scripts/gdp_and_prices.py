"""Render nominal/real GDP, the deflator, CPI, and inflation."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from common import load_example, setup

from macro_viz import IndexBase, TimeSeries
from macro_viz.accounts import analyze_gdp_series, calculate_inflation
from macro_viz.visuals import (
    gdp_deflator_canvas,
    gdp_levels_canvas,
    inflation_canvas,
    price_index_canvas,
)


def main(argv: Sequence[str] | None = None) -> None:
    args, output = setup(__doc__ or "", argv)
    data = load_example(args.data, "gdp_and_prices")
    dates = tuple(date(data["start_year"] + k, 1, 1) for k in range(len(data["nominal"])))
    nominal = TimeSeries(data["nominal_name"], dates, tuple(data["nominal"]), data["unit"])
    real = TimeSeries(data["real_name"], dates, tuple(data["real"]), data["unit"])
    gdp = analyze_gdp_series(nominal, real, base_period=dates[0])
    cpi = TimeSeries(
        data["cpi_name"], dates, tuple(data["cpi"]), data["index_unit"], IndexBase(dates[0])
    )
    inflation = calculate_inflation(cpi)
    suffix = args.suffix
    gdp_levels_canvas(gdp, title=data["title_levels"]).save(output / f"gdp_levels{suffix}")
    gdp_deflator_canvas(gdp, title=data["title_deflator"]).save(output / f"gdp_deflator{suffix}")
    price_index_canvas(cpi, title=data["title_cpi"]).save(output / f"cpi{suffix}")
    inflation_canvas(inflation, title=data["title_inflation"]).save(output / f"inflation{suffix}")


if __name__ == "__main__":
    main()
