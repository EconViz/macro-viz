from __future__ import annotations

from datetime import date

import pytest

from macro_viz import IndexBase, TimeSeries, ValidationError
from macro_viz.accounts import (
    GDPComponents,
    analyze_gdp_components,
    analyze_gdp_series,
    analyze_labor_market,
    calculate_inflation,
)

DATES = (date(2021, 1, 1), date(2022, 1, 1), date(2023, 1, 1), date(2024, 1, 1))


def series(
    name: str,
    values: tuple[float | None, ...],
    unit: str = "billions",
    index_base: IndexBase | None = None,
) -> TimeSeries:
    return TimeSeries(name, DATES, values, unit, index_base)


def test_gdp_expenditure_identity_and_component_shares() -> None:
    result = analyze_gdp_components(GDPComponents(600, 150, 200, -50, "billions USD"))

    assert result.total == 900
    assert result.shares.consumption == pytest.approx(66.6667, rel=1e-5)
    assert result.shares.investment == pytest.approx(16.6667, rel=1e-5)
    assert result.shares.government == pytest.approx(22.2222, rel=1e-5)
    assert result.shares.net_exports == pytest.approx(-5.5556, rel=1e-5)
    assert sum(
        (
            result.shares.consumption,
            result.shares.investment,
            result.shares.government,
            result.shares.net_exports,
        )
    ) == pytest.approx(100)


@pytest.mark.parametrize("value", [True, float("inf"), float("nan")])
def test_gdp_components_reject_non_numeric_finite_values(value: object) -> None:
    with pytest.raises(ValidationError, match="finite numbers"):
        GDPComponents(value, 1, 1, 1, "billions")  # type: ignore[arg-type]


def test_gdp_components_allow_negative_net_exports_but_not_negative_domestic_spending() -> None:
    assert analyze_gdp_components(GDPComponents(10, 5, 5, -2, "billions")).total == 18
    with pytest.raises(ValidationError, match="non-negative"):
        GDPComponents(10, -1, 5, 0, "billions")


def test_gdp_deflator_preserves_alignment_base_and_missing_values() -> None:
    nominal = series("Nominal GDP", (100, 126, None, 176))
    real = series("Real GDP", (100, 120, 130, 160))

    result = analyze_gdp_series(nominal, real, base_period=DATES[0])

    assert result.nominal is nominal
    assert result.real is real
    assert result.deflator.dates == DATES
    assert result.deflator.values == (100.0, 105.0, None, 110.0)
    assert result.deflator.unit == "index"
    assert result.deflator.index_base == IndexBase(DATES[0], 100)


def test_gdp_deflator_rejects_an_inconsistent_base_period() -> None:
    nominal = series("Nominal GDP", (110, 126, 140, 176))
    real = series("Real GDP", (100, 120, 130, 160))

    with pytest.raises(ValidationError, match="base period"):
        analyze_gdp_series(nominal, real, base_period=DATES[0])


def test_inflation_uses_lagged_percentage_change_and_propagates_missing_values() -> None:
    cpi = series("CPI", (100, 105, None, 115), "index", IndexBase(DATES[0]))

    result = calculate_inflation(cpi)

    assert result.price_index is cpi
    assert result.periods == 1
    assert result.inflation_rate.values[0] is None
    assert result.inflation_rate.values[1] == pytest.approx(5.0)
    assert result.inflation_rate.values[2:] == (None, None)
    assert result.inflation_rate.dates == cpi.dates
    assert result.inflation_rate.unit == "percent"
    assert result.inflation_rate.index_base is None


def test_multi_period_inflation_uses_the_requested_observation_lag() -> None:
    cpi = series("CPI", (100, 105, 110, 121), "index", IndexBase(DATES[0]))

    result = calculate_inflation(cpi, periods=2)

    assert result.inflation_rate.values[:2] == (None, None)
    assert result.inflation_rate.values[2] == pytest.approx(10.0)
    assert result.inflation_rate.values[3] == pytest.approx(15.238095)


def test_labor_market_derives_unemployment_levels_and_rates() -> None:
    labor_force = series("Labor force", (100, 102, None, 105), "millions")
    employment = series("Employment", (95, 96, 99, 100), "millions")

    result = analyze_labor_market(labor_force, employment)

    assert result.unemployment.values == (5.0, 6.0, None, 5.0)
    assert result.unemployment.unit == "millions"
    assert result.unemployment_rate.values[0] == 5.0
    assert result.unemployment_rate.values[1] == pytest.approx(5.882353)
    assert result.unemployment_rate.values[2] is None
    assert result.unemployment_rate.values[3] == pytest.approx(4.761905)
    assert result.unemployment_rate.unit == "percent"


@pytest.mark.parametrize(
    ("force", "employment", "message"),
    [
        ((0, 100, 100, 100), (0, 90, 90, 90), "labor force must be positive"),
        ((100, 100, 100, 100), (101, 90, 90, 90), "between zero"),
        ((100, 100, 100, 100), (-1, 90, 90, 90), "between zero"),
    ],
)
def test_labor_market_rejects_impossible_observed_levels(
    force: tuple[float, ...], employment: tuple[float, ...], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        analyze_labor_market(series("Labor force", force), series("Employment", employment))
