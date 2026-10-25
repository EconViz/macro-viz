"""Render trend, turning points, recessions, and output gaps."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from common import load_example, setup

from macro_viz import TimeSeries
from macro_viz.cycles import RecessionPeriod, analyze_business_cycle
from macro_viz.visuals import business_cycle_canvas, output_gap_canvas


def main(argv: Sequence[str] | None = None) -> None:
    args, output = setup(__doc__ or "", argv)
    data = load_example(args.data, "business_cycle")
    dates = tuple(date(data["start_year"] + k, 1, 1) for k in range(len(data["output"])))
    actual = TimeSeries(data["output_name"], dates, tuple(data["output"]), data["unit"])
    potential = TimeSeries(data["trend_name"], dates, tuple(data["trend"]), data["unit"])
    recessions = tuple(
        RecessionPeriod(date(start, 1, 1), date(end, 1, 1))
        for start, end in data["recession_years"]
    )
    result = analyze_business_cycle(actual, trend=potential, recessions=recessions)
    business_cycle_canvas(result, title=data["title_cycle"]).save(
        output / f"business_cycle{args.suffix}"
    )
    output_gap_canvas(result, title=data["title_gap"]).save(output / f"output_gap{args.suffix}")


if __name__ == "__main__":
    main()
