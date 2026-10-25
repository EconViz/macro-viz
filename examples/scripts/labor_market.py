"""Render employment, unemployment, and the unemployment rate."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from common import load_example, setup

from macro_viz import TimeSeries
from macro_viz.accounts import analyze_labor_market
from macro_viz.visuals import labor_market_canvas, unemployment_rate_canvas


def main(argv: Sequence[str] | None = None) -> None:
    args, output = setup(__doc__ or "", argv)
    data = load_example(args.data, "labor_market")
    dates = tuple(date(data["start_year"] + k, 1, 1) for k in range(len(data["employment"])))
    labor_force = TimeSeries(
        data["labor_force_name"], dates, tuple(data["labor_force"]), data["unit"]
    )
    employment = TimeSeries(data["employment_name"], dates, tuple(data["employment"]), data["unit"])
    result = analyze_labor_market(labor_force, employment)
    labor_market_canvas(result, title=data["title_levels"]).save(
        output / f"labor_market{args.suffix}"
    )
    unemployment_rate_canvas(result, title=data["title_rate"]).save(
        output / f"unemployment_rate{args.suffix}"
    )


if __name__ == "__main__":
    main()
