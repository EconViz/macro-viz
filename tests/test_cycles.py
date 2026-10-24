from __future__ import annotations

from datetime import date

import pytest

from macro_viz import TimeSeries, ValidationError
from macro_viz.cycles import (
    RecessionPeriod,
    TurningPointKind,
    analyze_business_cycle,
    linear_trend,
)

DATES = tuple(date(year, 1, 1) for year in range(2018, 2025))


def output(values: tuple[float | None, ...]) -> TimeSeries:
    return TimeSeries("Real GDP", DATES, values, "billions USD")


def test_linear_trend_fits_observed_values_and_returns_all_dates() -> None:
    trend = linear_trend(output((100, None, 120, 130, 140, 150, 160)))

    assert trend.name == "Real GDP trend"
    assert trend.dates == DATES
    assert trend.unit == "billions USD"
    assert trend.values[0] == pytest.approx(100, abs=0.03)
    assert trend.values[-1] == pytest.approx(160, abs=0.03)
    assert all(value is not None for value in trend.values)


def test_business_cycle_reports_gap_turning_points_and_recessions() -> None:
    actual = output((100, 110, 105, 115, 108, None, 120))
    potential = output((100, 105, 107, 110, 112, 115, 118))
    recessions = (RecessionPeriod(DATES[2], DATES[4]),)

    result = analyze_business_cycle(actual, trend=potential, recessions=recessions)

    assert result.output is actual
    assert result.trend is potential
    assert result.output_gap.values[0] == 0.0
    assert result.output_gap.values[1] == pytest.approx(4.761905)
    assert result.output_gap.values[2] == pytest.approx(-1.869159)
    assert result.output_gap.values[3] == pytest.approx(4.545455)
    assert result.output_gap.values[4] == pytest.approx(-3.571429)
    assert result.output_gap.values[5] is None
    assert result.output_gap.values[6] == pytest.approx(1.694915)
    assert [(point.period, point.value, point.kind) for point in result.turning_points] == [
        (DATES[1], 110.0, TurningPointKind.PEAK),
        (DATES[2], 105.0, TurningPointKind.TROUGH),
        (DATES[3], 115.0, TurningPointKind.PEAK),
    ]
    assert result.recessions == recessions


def test_turning_points_do_not_bridge_missing_observations() -> None:
    result = analyze_business_cycle(
        output((100, 110, None, 120, 100, 110, 120)),
        trend=output((100, 100, 100, 100, 100, 100, 100)),
    )

    assert result.turning_points == (result.turning_points[0],)
    assert result.turning_points[0].period == DATES[4]
    assert result.turning_points[0].kind is TurningPointKind.TROUGH


def test_recession_periods_must_be_ordered_and_non_overlapping() -> None:
    actual = output((100, 101, 102, 103, 104, 105, 106))
    periods = (
        RecessionPeriod(DATES[3], DATES[4]),
        RecessionPeriod(DATES[2], DATES[3]),
    )

    with pytest.raises(ValidationError, match="ordered and non-overlapping"):
        analyze_business_cycle(actual, recessions=periods)


def test_output_gap_rejects_nonpositive_observed_trend() -> None:
    with pytest.raises(ValidationError, match="trend values must be positive"):
        analyze_business_cycle(
            output((100, 101, 102, 103, 104, 105, 106)),
            trend=output((100, 101, 0, 103, 104, 105, 106)),
        )
