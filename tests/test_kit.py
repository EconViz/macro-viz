from __future__ import annotations

from collections.abc import Iterator

import pytest
from mosaickit import PathLayer, TextLayer

from macro_viz import Config
from macro_viz.visuals._kit import (
    axes_layers,
    canvas_spec,
    is_symbol,
    new_canvas,
)


@pytest.fixture(autouse=True)
def _reset_config() -> Iterator[None]:
    yield
    Config.reset()


def test_symbols_are_math_and_words_are_not() -> None:
    assert is_symbol("Y") and is_symbol("$i^*$")
    assert not is_symbol("percent")


def test_axes_have_arrowheads_and_titles_past_the_tips() -> None:
    layers = {
        layer.id: layer
        for layer in axes_layers((0, 10), (0, 8), x_label="Y", y_label="percent", origin_label="0")
    }

    assert isinstance(layers["axes.x"], PathLayer)
    assert layers["axes.x"].stroke is not None and layers["axes.x"].stroke.arrow is not None
    x_label = layers["axes.x.label"]
    y_label = layers["axes.y.label"]
    assert isinstance(x_label, TextLayer) and isinstance(y_label, TextLayer)
    assert x_label.math and x_label.anchor == "left"
    assert not y_label.math and y_label.anchor == "bottom"
    assert "axes.origin.label" in layers


def test_no_titles_are_drawn_without_labels() -> None:
    ids = {layer.id for layer in axes_layers((0, 1), (0, 1), x_label=None, y_label="")}

    assert ids == {"axes.x", "axes.y"}


def test_group_nudges_from_the_settings_move_labels_by_group() -> None:
    Config.from_dict(
        {"macro": {"label": {"curve": {"top": "3pt", "right": "2pt"}, "mark": {"left": "4pt"}}}}
    ).use()
    canvas = new_canvas(canvas_spec((0, 1), (0, 1), width=3, height=3, title=None))
    canvas.add(TextLayer((0, 0), "A", id="macro.test.curve.label", role="macro.curve.primary"))
    canvas.add(TextLayer((0, 0), "B", id="macro.test.mark", role="macro.mark"))
    canvas.add(TextLayer((0, 0), "C", id="axes.x.label", role="axes"))
    layers = {layer.id: layer for layer in canvas.snapshot().layers}

    assert layers["macro.test.curve.label"].nudge.dy > 0  # type: ignore[attr-defined]
    assert layers["macro.test.curve.label"].nudge.dx > 0  # type: ignore[attr-defined]
    assert layers["macro.test.mark"].nudge.dx < 0  # type: ignore[attr-defined]
    assert layers["axes.x.label"].nudge is None  # type: ignore[attr-defined]


def test_without_settings_labels_carry_no_nudge() -> None:
    canvas = new_canvas(canvas_spec((0, 1), (0, 1), width=3, height=3, title=None))
    canvas.add(TextLayer((0, 0), "A", id="macro.test.curve.label", role="macro.curve.primary"))

    assert canvas.snapshot().layers[0].nudge is None  # type: ignore[attr-defined]
