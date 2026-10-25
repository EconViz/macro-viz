from __future__ import annotations

from collections.abc import Iterator
from datetime import date

import pytest

from macro_viz import Config, TimeSeries, ValidationError
from macro_viz.accounts import calculate_inflation
from macro_viz.i18n import LANGUAGES, label_table, text, validate_language
from macro_viz.visuals import gdp_decomposition_canvas  # noqa: F401


@pytest.fixture(autouse=True)
def _reset_config() -> Iterator[None]:
    yield
    Config.reset()


def test_every_language_has_the_same_label_ids() -> None:
    reference = set(label_table("en"))

    assert all(set(label_table(language)) == reference for language in LANGUAGES)
    assert all(label_table(language)[key] for language in LANGUAGES for key in reference)


def test_text_fills_placeholders_and_rejects_unknown_ids() -> None:
    assert text("series.trend_of", language="en", name="GDP") == "GDP trend"
    assert text("series.trend_of", language="zh-TW", name="GDP") == "GDP趨勢"
    with pytest.raises(ValidationError):
        text("no.such.id", language="en")
    with pytest.raises(ValidationError):
        validate_language("fr")


def test_the_configured_language_names_derived_series() -> None:
    dates = (date(2023, 1, 1), date(2024, 1, 1))
    from macro_viz import IndexBase

    cpi = TimeSeries("CPI", dates, (100.0, 103.0), "index", IndexBase(dates[0]))

    english = calculate_inflation(cpi)
    Config.from_dict({"macro": {"language": "zh-TW"}}).use()
    chinese = calculate_inflation(cpi)
    named = calculate_inflation(cpi, name="Own name")

    assert english.inflation_rate.name == "CPI inflation"
    assert chinese.inflation_rate.name == "CPI通貨膨脹率"
    assert chinese.inflation_rate.unit == "百分比"
    assert named.inflation_rate.name == "Own name"
