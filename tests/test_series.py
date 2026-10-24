from __future__ import annotations

from datetime import date

import pytest

from macro_viz import IndexBase, TimeSeries, ValidationError

DATES = (date(2022, 1, 1), date(2023, 1, 1), date(2024, 1, 1))


def test_series_normalizes_real_values_and_counts_missing_observations() -> None:
    series = TimeSeries("Output", DATES, (100, None, 110.5), "billions")

    assert series.values == (100.0, None, 110.5)
    assert series.observed_count == 2


@pytest.mark.parametrize(
    ("dates", "values", "message"),
    [
        ((), (), "at least one date"),
        (DATES, (1.0,), "same length"),
        ((DATES[1], DATES[0]), (1.0, 2.0), "strictly increasing"),
        ((DATES[0], DATES[0]), (1.0, 2.0), "strictly increasing"),
        (DATES, (1.0, float("nan"), 2.0), "finite numbers or None"),
        (DATES, (1.0, True, 2.0), "finite numbers or None"),
    ],
)
def test_series_rejects_ambiguous_or_invalid_observations(
    dates: tuple[date, ...], values: tuple[object, ...], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        TimeSeries("Output", dates, values, "billions")  # type: ignore[arg-type]


def test_series_alignment_checks_dates_and_units_independently() -> None:
    output = TimeSeries("Output", DATES, (100, 101, 102), "billions")
    percent = TimeSeries("Growth", DATES, (1, 2, 3), "percent")

    with pytest.raises(ValidationError, match="same unit"):
        output.require_aligned(percent)
    output.require_aligned(percent, same_unit=False)


def test_index_base_must_name_a_present_period_and_matching_value() -> None:
    with pytest.raises(ValidationError, match="present"):
        TimeSeries(
            "CPI",
            DATES,
            (100, 105, 110),
            "index",
            index_base=IndexBase(date(2021, 1, 1)),
        )

    with pytest.raises(ValidationError, match="base value"):
        TimeSeries(
            "CPI",
            DATES,
            (99, 105, 110),
            "index",
            index_base=IndexBase(DATES[0]),
        )


def test_index_base_rejects_boolean_and_nonfinite_values() -> None:
    with pytest.raises(ValidationError, match="positive and finite"):
        IndexBase(DATES[0], True)
    with pytest.raises(ValidationError, match="positive and finite"):
        IndexBase(DATES[0], float("inf"))


def test_with_values_preserves_dates_and_replaces_requested_metadata() -> None:
    source = TimeSeries("CPI", DATES, (100, 105, 110), "index", IndexBase(DATES[0]))

    growth = source.with_values(
        (None, 5, 4.7619), name="Inflation", unit="percent", index_base=None
    )

    assert growth.dates is source.dates
    assert growth.name == "Inflation"
    assert growth.unit == "percent"
    assert growth.index_base is None
