"""Renderer-neutral dated series shared by macroeconomic analyses."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from numbers import Real
from typing import TypeAlias

from macro_viz.errors import ValidationError

Observation: TypeAlias = float | None


@dataclass(frozen=True, slots=True)
class IndexBase:
    """The reference period and value attached to a price index."""

    period: date
    value: float = 100.0

    def __post_init__(self) -> None:
        if not isinstance(self.period, date):
            raise ValidationError("index base period must be a date")
        if not math.isfinite(self.value) or self.value <= 0:
            raise ValidationError("index base value must be positive and finite")


@dataclass(frozen=True, slots=True)
class TimeSeries:
    """A dated series whose missing observations are represented only by ``None``.

    Dates and values are positional and immutable. Units are opaque labels retained by every
    transformation; an index additionally carries its reference period and value.
    """

    name: str
    dates: tuple[date, ...]
    values: tuple[Observation, ...]
    unit: str
    index_base: IndexBase | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValidationError("series name must be non-empty")
        if not isinstance(self.unit, str) or not self.unit.strip():
            raise ValidationError("series unit must be non-empty")
        dates = tuple(self.dates)
        values = tuple(self.values)
        if not dates:
            raise ValidationError("series must contain at least one date")
        if len(dates) != len(values):
            raise ValidationError("series dates and values must have the same length")
        if not all(isinstance(item, date) for item in dates):
            raise ValidationError("series dates must be date objects")
        if any(left >= right for left, right in zip(dates, dates[1:], strict=False)):
            raise ValidationError("series dates must be strictly increasing")
        cleaned: list[Observation] = []
        for value in values:
            if value is None:
                cleaned.append(None)
            elif isinstance(value, bool) or not isinstance(value, Real):
                raise ValidationError("series values must be finite numbers or None")
            elif not math.isfinite(value):
                raise ValidationError("series values must be finite numbers or None")
            else:
                cleaned.append(float(value))
        if self.index_base is not None and self.index_base.period not in dates:
            raise ValidationError("index base period must be present in the series dates")
        if self.index_base is not None:
            base_value = cleaned[dates.index(self.index_base.period)]
            if base_value is None or not math.isclose(
                base_value, self.index_base.value, rel_tol=1e-9, abs_tol=1e-9
            ):
                raise ValidationError(
                    "series observation at the index base must equal its base value"
                )
        object.__setattr__(self, "dates", dates)
        object.__setattr__(self, "values", tuple(cleaned))

    @property
    def observed_count(self) -> int:
        """Number of non-missing observations."""
        return sum(value is not None for value in self.values)

    def require_aligned(self, other: TimeSeries, *, same_unit: bool = True) -> None:
        """Raise when *other* does not share dates and, by default, units."""
        if self.dates != other.dates:
            raise ValidationError(f"{self.name} and {other.name} must have identical dates")
        if same_unit and self.unit != other.unit:
            raise ValidationError(f"{self.name} and {other.name} must use the same unit")

    def with_values(
        self,
        values: tuple[Observation, ...],
        *,
        name: str | None = None,
        unit: str | None = None,
        index_base: IndexBase | None = None,
    ) -> TimeSeries:
        """Return a series on the same dates with replacement values and metadata."""
        return TimeSeries(
            name=name or self.name,
            dates=self.dates,
            values=values,
            unit=unit or self.unit,
            index_base=index_base,
        )
