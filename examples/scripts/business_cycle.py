"""Render trend, turning points, recessions, and output gaps."""

from __future__ import annotations

from datetime import date

from common import prepare_manual_output

from macro_viz import TimeSeries
from macro_viz.cycles import RecessionPeriod, analyze_business_cycle
from macro_viz.visuals import business_cycle_canvas, output_gap_canvas


def main() -> None:
    output = prepare_manual_output()
    dates = tuple(date(year, 1, 1) for year in range(2016, 2025))
    actual = TimeSeries(
        "Real GDP",
        dates,
        (980, 1010, 1045, 1080, 1030, 1095, 1140, 1125, 1180),
        "billions USD",
    )
    potential = TimeSeries(
        "Potential GDP",
        dates,
        (985, 1010, 1035, 1060, 1085, 1110, 1135, 1160, 1185),
        "billions USD",
    )
    result = analyze_business_cycle(
        actual,
        trend=potential,
        recessions=(RecessionPeriod(dates[4], dates[4]),),
    )

    business_cycle_canvas(result, title="Business cycle").save(output / "business_cycle.png")
    output_gap_canvas(result, title="Output gap").save(output / "output_gap.png")


if __name__ == "__main__":
    main()
