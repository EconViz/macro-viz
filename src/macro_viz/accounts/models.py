"""Typed renderer-neutral results for national accounts."""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real

from macro_viz.errors import ValidationError
from macro_viz.series import TimeSeries


@dataclass(frozen=True, slots=True)
class GDPComponents:
    """Expenditure components in one common currency unit."""

    consumption: float
    investment: float
    government: float
    net_exports: float
    unit: str

    def __post_init__(self) -> None:
        values = (self.consumption, self.investment, self.government, self.net_exports)
        if not all(
            not isinstance(value, bool) and isinstance(value, Real) and math.isfinite(value)
            for value in values
        ):
            raise ValidationError("GDP components must be finite numbers")
        if min(self.consumption, self.investment, self.government) < 0:
            raise ValidationError("consumption, investment, and government must be non-negative")
        if not isinstance(self.unit, str) or not self.unit.strip():
            raise ValidationError("GDP component unit must be non-empty")


@dataclass(frozen=True, slots=True)
class GDPComponentShares:
    """Each expenditure component as a percentage of GDP."""

    consumption: float
    investment: float
    government: float
    net_exports: float


@dataclass(frozen=True, slots=True)
class GDPDecompositionResult:
    """The GDP identity and its component shares."""

    components: GDPComponents
    total: float
    shares: GDPComponentShares


@dataclass(frozen=True, slots=True)
class GDPSeriesResult:
    """Aligned nominal GDP, real GDP, and GDP deflator series."""

    nominal: TimeSeries
    real: TimeSeries
    deflator: TimeSeries


@dataclass(frozen=True, slots=True)
class InflationResult:
    """A price index and its percentage change over ``periods`` observations."""

    price_index: TimeSeries
    inflation_rate: TimeSeries
    periods: int


@dataclass(frozen=True, slots=True)
class LaborMarketResult:
    """Aligned labour-force levels and unemployment rate."""

    labor_force: TimeSeries
    employment: TimeSeries
    unemployment: TimeSeries
    unemployment_rate: TimeSeries
