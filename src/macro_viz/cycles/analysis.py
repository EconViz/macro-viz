"""Business-cycle trend, output-gap, and turning-point calculations."""

from __future__ import annotations

from macro_viz.cycles.models import (
    BusinessCycleResult,
    RecessionPeriod,
    TurningPoint,
    TurningPointKind,
)
from macro_viz.errors import ValidationError
from macro_viz.i18n import text
from macro_viz.series import Observation, TimeSeries


def linear_trend(output: TimeSeries, *, name: str | None = None) -> TimeSeries:
    """Fit an OLS linear trend against calendar-day ordinals, ignoring missing values."""
    observed = [
        (float(period.toordinal()), value)
        for period, value in zip(output.dates, output.values, strict=True)
        if value is not None
    ]
    if len(observed) < 2:
        raise ValidationError("linear trend requires at least two observed values")
    x_mean = sum(x for x, _ in observed) / len(observed)
    y_mean = sum(value for _, value in observed) / len(observed)
    denominator = sum((x - x_mean) ** 2 for x, _ in observed)
    if denominator == 0:
        raise ValidationError("linear trend requires distinct dates")
    slope = sum((x - x_mean) * (value - y_mean) for x, value in observed) / denominator
    intercept = y_mean - slope * x_mean
    return TimeSeries(
        name=name or text("series.trend_of", name=output.name),
        dates=output.dates,
        values=tuple(intercept + slope * period.toordinal() for period in output.dates),
        unit=output.unit,
    )


def _turning_points(output: TimeSeries) -> tuple[TurningPoint, ...]:
    points: list[TurningPoint] = []
    for index in range(1, len(output.values) - 1):
        previous, current, following = output.values[index - 1 : index + 2]
        if previous is None or current is None or following is None:
            continue
        if current > previous and current > following:
            kind = TurningPointKind.PEAK
        elif current < previous and current < following:
            kind = TurningPointKind.TROUGH
        else:
            continue
        points.append(TurningPoint(output.dates[index], current, kind))
    return tuple(points)


def analyze_business_cycle(
    output: TimeSeries,
    *,
    trend: TimeSeries | None = None,
    recessions: tuple[RecessionPeriod, ...] = (),
    gap_name: str | None = None,
) -> BusinessCycleResult:
    """Combine output, trend, percentage gaps, turning points, and recession metadata."""
    resolved_trend = trend or linear_trend(output)
    output.require_aligned(resolved_trend)
    if any(value is not None and value <= 0 for value in output.values):
        raise ValidationError("observed output values must be positive")
    if any(value is not None and value <= 0 for value in resolved_trend.values):
        raise ValidationError("observed trend values must be positive")
    ordered_recessions = tuple(recessions)
    if any(
        left.end >= right.start
        for left, right in zip(ordered_recessions, ordered_recessions[1:], strict=False)
    ):
        raise ValidationError("recession periods must be ordered and non-overlapping")
    gaps: list[Observation] = []
    for actual, potential in zip(output.values, resolved_trend.values, strict=True):
        if actual is None or potential is None:
            gaps.append(None)
        else:
            gaps.append(100 * (actual - potential) / potential)
    gap = TimeSeries(
        name=gap_name or text("series.output_gap"),
        dates=output.dates,
        values=tuple(gaps),
        unit=text("unit.percent"),
    )
    return BusinessCycleResult(
        output=output,
        trend=resolved_trend,
        output_gap=gap,
        turning_points=_turning_points(output),
        recessions=ordered_recessions,
    )
