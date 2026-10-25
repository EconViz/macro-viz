"""Tests that fail when a figure's text, numbers, or style are written into the logic."""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest

from macro_viz import Config, TimeSeries
from macro_viz.accounts import GDPComponents, analyze_gdp_components, analyze_labor_market
from macro_viz.cycles import analyze_business_cycle
from macro_viz.visuals import (
    business_cycle_canvas,
    gdp_decomposition_canvas,
    unemployment_rate_canvas,
)

SOURCE = Path(__file__).parents[1] / "src" / "macro_viz"
FONT_NAMES = re.compile(
    r"\b(pagella|dejavu|helvetica|arial|times new roman|noto|georgia|courier)\b", re.IGNORECASE
)
DATES = tuple(date(year, 1, 1) for year in range(2019, 2025))


@pytest.fixture(autouse=True)
def _reset_config() -> Iterator[None]:
    yield
    Config.reset()


def _sources() -> Iterator[Path]:
    return (path for path in SOURCE.rglob("*.py"))


def test_source_has_no_absolute_paths() -> None:
    pattern = re.compile(r"""["'](/Users|/home|/tmp|/var|/opt|[A-Za-z]:\\)""")

    assert [str(p) for p in _sources() if pattern.search(p.read_text("utf-8"))] == []


def test_source_has_no_colour_literals() -> None:
    pattern = re.compile(r"""["']#[0-9A-Fa-f]{3,8}["']""")

    assert [str(p) for p in _sources() if pattern.search(p.read_text("utf-8"))] == []


def test_source_names_no_font() -> None:
    offenders = [str(path) for path in _sources() if FONT_NAMES.search(path.read_text("utf-8"))]

    assert offenders == []


def test_a_title_argument_reaches_the_figure() -> None:
    result = analyze_gdp_components(GDPComponents(60, 20, 25, -5, "billions"))

    titles = {
        title: next(
            layer.text  # type: ignore[attr-defined]
            for layer in gdp_decomposition_canvas(result, title=title).snapshot().layers
            if layer.id == "macro.title"
        )
        for title in ("First", "Second")
    }

    assert titles == {"First": "First", "Second": "Second"}


def test_changing_the_economics_changes_the_figure() -> None:
    def first_level(consumption: float) -> tuple[object, ...]:
        result = analyze_gdp_components(GDPComponents(consumption, 20, 25, -5, "billions"))
        layers = gdp_decomposition_canvas(result).snapshot().layers
        return next(
            layer.boundary  # type: ignore[attr-defined]
            for layer in layers
            if layer.id == "macro.accounts.gdp.component.consumption"
        )

    assert first_level(60) != first_level(70)


def test_the_y_title_and_series_names_come_from_the_data() -> None:
    def labels(unit: str, name: str) -> set[object]:
        force = TimeSeries("Force", DATES, (100, 101, 102, 103, 104, 105), unit)
        employed = TimeSeries("Employed", DATES, (95, 96, 97, 98, 99, 100), unit)
        result = analyze_labor_market(force, employed, unemployment_rate_name=name)
        layers = unemployment_rate_canvas(result).snapshot().layers
        return {
            layer.text  # type: ignore[attr-defined]
            for layer in layers
            if layer.id.endswith(".label")
        }

    assert labels("millions", "Rate A") != labels("thousands", "Rate B")


def test_widths_and_sizes_come_from_the_settings() -> None:
    from macro_viz.themes import build_theme

    thin = Config.from_dict({"macro": {"stroke": {"curve": 1.5}, "text": {"scale": 2}}})
    heavy = Config.from_dict({"macro": {"stroke": {"curve": 5}}})

    assert thin.settings.options.curve_width == 1.5
    assert heavy.settings.options.curve_width == 5
    assert thin.settings.options.text_scale == 2
    role = build_theme(thin.settings.options).resolve(
        "macro.curve.primary", fallback_category="path"
    )
    assert role.stroke is not None and role.stroke.width == 1.5


def test_business_cycle_range_follows_the_data() -> None:
    def top(scale: float) -> float:
        output = TimeSeries("Output", DATES, tuple(100 * scale + i for i in range(6)), "units")
        trend = TimeSeries("Trend", DATES, tuple(100 * scale + i for i in range(6)), "units")
        return business_cycle_canvas(analyze_business_cycle(output, trend=trend)).spec.y_max

    assert top(1) < top(10)
