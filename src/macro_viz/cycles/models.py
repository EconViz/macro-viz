"""Typed renderer-neutral business-cycle results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from macro_viz.errors import ValidationError
from macro_viz.series import TimeSeries


class TurningPointKind(str, Enum):
    """Direction of a local business-cycle turning point."""

    PEAK = "peak"
    TROUGH = "trough"


@dataclass(frozen=True, slots=True)
class TurningPoint:
    """A strict local peak or trough in the observed output series."""

    period: date
    value: float
    kind: TurningPointKind


@dataclass(frozen=True, slots=True)
class RecessionPeriod:
    """Inclusive recession interval used for figure shading."""

    start: date
    end: date

    def __post_init__(self) -> None:
        if not isinstance(self.start, date) or not isinstance(self.end, date):
            raise ValidationError("recession bounds must be dates")
        if self.start > self.end:
            raise ValidationError("recession start must not follow its end")


@dataclass(frozen=True, slots=True)
class BusinessCycleResult:
    """Observed output, trend, gap, turning points, and recession intervals."""

    output: TimeSeries
    trend: TimeSeries
    output_gap: TimeSeries
    turning_points: tuple[TurningPoint, ...]
    recessions: tuple[RecessionPeriod, ...]
