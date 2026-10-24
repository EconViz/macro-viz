"""National-account identities and time-series transformations."""

from __future__ import annotations

from datetime import date

from macro_viz.accounts.models import (
    GDPComponents,
    GDPComponentShares,
    GDPDecompositionResult,
    GDPSeriesResult,
    InflationResult,
    LaborMarketResult,
)
from macro_viz.errors import ValidationError
from macro_viz.series import IndexBase, Observation, TimeSeries


def analyze_gdp_components(components: GDPComponents) -> GDPDecompositionResult:
    """Evaluate ``Y = C + I + G + NX`` and component shares."""
    total = (
        components.consumption
        + components.investment
        + components.government
        + components.net_exports
    )
    if total <= 0:
        raise ValidationError("GDP total must be positive")
    shares = GDPComponentShares(
        consumption=100 * components.consumption / total,
        investment=100 * components.investment / total,
        government=100 * components.government / total,
        net_exports=100 * components.net_exports / total,
    )
    return GDPDecompositionResult(components=components, total=total, shares=shares)


def analyze_gdp_series(
    nominal: TimeSeries, real: TimeSeries, *, base_period: date
) -> GDPSeriesResult:
    """Calculate the GDP deflator as ``100 * nominal / real``.

    A missing nominal or real observation produces a missing deflator. Observed real GDP must be
    strictly positive. Nominal and real GDP retain their original common unit.
    """
    nominal.require_aligned(real)
    if base_period not in nominal.dates:
        raise ValidationError("GDP deflator base period must be present in the series dates")
    if any(value is not None and value <= 0 for value in nominal.values):
        raise ValidationError("observed nominal GDP must be positive")
    if any(value is not None and value <= 0 for value in real.values):
        raise ValidationError("observed real GDP must be positive")
    values: list[Observation] = []
    for nominal_value, real_value in zip(nominal.values, real.values, strict=True):
        if nominal_value is None or real_value is None:
            values.append(None)
        elif real_value <= 0:
            raise ValidationError("observed real GDP must be positive")
        else:
            values.append(100 * nominal_value / real_value)
    base_value = values[nominal.dates.index(base_period)]
    if base_value is None or not abs(base_value - 100) <= 1e-9:
        raise ValidationError("nominal and real GDP must agree in the base period")
    deflator = TimeSeries(
        name="GDP deflator",
        dates=nominal.dates,
        values=tuple(values),
        unit="index",
        index_base=IndexBase(base_period),
    )
    return GDPSeriesResult(nominal=nominal, real=real, deflator=deflator)


def calculate_inflation(price_index: TimeSeries, *, periods: int = 1) -> InflationResult:
    """Calculate percentage price-index changes with explicit missing propagation."""
    if price_index.index_base is None:
        raise ValidationError("price index must declare its index base")
    if isinstance(periods, bool) or not isinstance(periods, int) or periods < 1:
        raise ValidationError("inflation periods must be a positive integer")
    if periods >= len(price_index.values):
        raise ValidationError("inflation periods must be shorter than the series")
    if any(value is not None and value <= 0 for value in price_index.values):
        raise ValidationError("observed price-index values must be positive")
    values: list[Observation] = [None] * periods
    for current, previous in zip(
        price_index.values[periods:], price_index.values[:-periods], strict=True
    ):
        if current is None or previous is None:
            values.append(None)
        elif previous <= 0 or current <= 0:
            raise ValidationError("observed price-index values must be positive")
        else:
            values.append(100 * (current - previous) / previous)
    inflation = TimeSeries(
        name=f"{price_index.name} inflation",
        dates=price_index.dates,
        values=tuple(values),
        unit="percent",
    )
    return InflationResult(price_index=price_index, inflation_rate=inflation, periods=periods)


def analyze_labor_market(labor_force: TimeSeries, employment: TimeSeries) -> LaborMarketResult:
    """Derive unemployment levels and rates from labour force and employment."""
    labor_force.require_aligned(employment)
    if any(value is not None and value <= 0 for value in labor_force.values):
        raise ValidationError("observed labor force must be positive")
    if any(value is not None and value < 0 for value in employment.values):
        raise ValidationError("observed employment must be non-negative")
    unemployed: list[Observation] = []
    rates: list[Observation] = []
    for force, employed in zip(labor_force.values, employment.values, strict=True):
        if force is None or employed is None:
            unemployed.append(None)
            rates.append(None)
        elif employed > force:
            raise ValidationError("observed employment must not exceed the labor force")
        else:
            count = force - employed
            unemployed.append(count)
            rates.append(100 * count / force)
    unemployment = labor_force.with_values(tuple(unemployed), name="Unemployment", index_base=None)
    unemployment_rate = labor_force.with_values(
        tuple(rates), name="Unemployment rate", unit="percent", index_base=None
    )
    return LaborMarketResult(
        labor_force=labor_force,
        employment=employment,
        unemployment=unemployment,
        unemployment_rate=unemployment_rate,
    )
