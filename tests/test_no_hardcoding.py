"""Tests that fail when a figure's text, numbers, or style are written into the logic."""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from pathlib import Path

import pytest

from macro_viz import Config
from macro_viz.keynesian import ConsumptionFunction, KeynesianCross
from macro_viz.visuals import keynesian_cross_canvas

SOURCE = Path(__file__).parents[1] / "src" / "macro_viz"
FONT_NAMES = re.compile(
    r"\b(pagella|dejavu|helvetica|arial|times new roman|noto|georgia|courier)\b", re.IGNORECASE
)


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


def _keynesian() -> KeynesianCross:
    return KeynesianCross(ConsumptionFunction(20, 0.6), investment=20, government=30, taxes=20)


def test_a_title_argument_reaches_the_figure() -> None:
    assert keynesian_cross_canvas(_keynesian()).spec.title is None
    titles = {
        title: keynesian_cross_canvas(_keynesian(), title=title).spec.title
        for title in ("First", "Second")
    }

    assert titles == {"First": "First", "Second": "Second"}


def test_changing_the_economics_changes_the_figure() -> None:
    def demand_path(propensity: float) -> object:
        model = KeynesianCross(ConsumptionFunction(20, propensity), 20, 30, 20)
        layers = keynesian_cross_canvas(model, x_max=300).snapshot().layers
        return next(
            layer.path  # type: ignore[attr-defined]
            for layer in layers
            if layer.id == "macro.keynesian.demand"
        )

    assert demand_path(0.5) != demand_path(0.7)


def test_axis_ranges_and_sample_counts_are_arguments() -> None:
    model = _keynesian()
    coarse = keynesian_cross_canvas(model, x_max=300, samples=5)
    fine = keynesian_cross_canvas(model, x_max=300, samples=50)

    def length(canvas: object) -> int:
        layers = canvas.snapshot().layers  # type: ignore[attr-defined]
        demand = next(item for item in layers if item.id == "macro.keynesian.demand")
        return len(demand.path)

    assert length(coarse) < length(fine)
    assert keynesian_cross_canvas(model, x_max=300).spec.x_max == 300
    assert keynesian_cross_canvas(model, x_max=400).spec.x_max == 400


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


TRANSMISSION = SOURCE / "visuals" / "transmission"
ALLOWED_NUMBERS = {0, 1, 2}
"""Bare numbers a drawing function may use: zero, one, and two (a mean or a pair)."""
PRESET_FILES = {"_preset.py"}
"""The one module that holds the derivations' visual constants, each with its own docstring."""


def _bare_numbers(path: Path) -> list[tuple[int, object]]:
    """Every numeric literal of ``path`` other than 0, 1, 2 and their negatives."""
    found: list[tuple[int, object]] = []
    for node in ast.walk(ast.parse(path.read_text("utf-8"))):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, (int, float))
            and not isinstance(node.value, bool)
            and abs(node.value) not in ALLOWED_NUMBERS
        ):
            found.append((node.lineno, node.value))
    return sorted(found)


def test_transmission_figures_hold_no_bare_numbers() -> None:
    offenders = [
        f"{path.relative_to(SOURCE)}:{line}: {value}"
        for path in sorted(TRANSMISSION.glob("*.py"))
        if path.name not in PRESET_FILES
        for line, value in _bare_numbers(path)
    ]

    assert offenders == [], "move these numbers to _preset.py or the configuration"


MAX_LINES = 450
"""A source file longer than this should be split into a package of smaller modules."""


def test_no_source_file_exceeds_the_line_limit() -> None:
    lines = {
        path.relative_to(SOURCE).as_posix(): len(path.read_text("utf-8").splitlines())
        for path in _sources()
    }
    offenders = [
        f"{name}: {count} lines" for name, count in sorted(lines.items()) if count > MAX_LINES
    ]

    assert offenders == []
