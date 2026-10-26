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
    canvas.add(PathLayer(((0, 0), (1, 1)), id="macro.test.curve", role="macro.curve.primary"))
    canvas.add(TextLayer((1, 1), "A", id="macro.test.curve.label", role="macro.curve.primary"))
    canvas.add(TextLayer((0, 0), "B", id="macro.test.mark", role="macro.mark"))
    canvas.add(TextLayer((0, 0), "C", id="axes.x.label", role="axes"))
    layers = {layer.id: layer for layer in canvas.snapshot().layers}

    assert layers["macro.test.curve.label"].nudge.dy > 0  # type: ignore[attr-defined]
    assert layers["macro.test.curve.label"].nudge.dx > 0  # type: ignore[attr-defined]
    assert layers["macro.test.mark"].nudge.dx < 0  # type: ignore[attr-defined]
    assert layers["axes.x.label"].nudge is None  # type: ignore[attr-defined]


def test_without_settings_labels_carry_no_nudge() -> None:
    canvas = new_canvas(canvas_spec((0, 1), (0, 1), width=3, height=3, title=None))
    canvas.add(PathLayer(((0, 0), (1, 1)), id="macro.test.curve", role="macro.curve.primary"))
    canvas.add(TextLayer((1, 1), "A", id="macro.test.curve.label", role="macro.curve.primary"))

    assert canvas.snapshot().layers[1].nudge is None  # type: ignore[attr-defined]


def test_moved_curves_and_movement_arrows_are_solid_and_thinner_than_curves() -> None:
    from macro_viz.themes import MANUAL_THEME

    def stroke(role: str):  # type: ignore[no-untyped-def]
        return MANUAL_THEME.resolve(role, fallback_category="path").stroke

    heavy = stroke("macro.curve.primary").width
    for role in ("macro.curve.primary.shifted", "macro.curve.secondary.shifted", "macro.movement"):
        found = stroke(role)
        assert found.dash.value == "solid", role
        assert found.width < heavy, role


def test_shift_is_straight_and_rotation_opens_toward_the_vertical_centreline() -> None:
    from mosaickit import ArrowLayer

    from macro_viz.visuals._theory import rotation_arrow, shift_arrow

    assert isinstance(shift_arrow((1.0, 2.0), (3.0, 2.0), layer_id="s"), ArrowLayer)
    for start, end, pivot, direction in (
        ((2.0, 5.0), (3.0, 6.0), (5.0, 5.0), -1.0),
        ((8.0, 5.0), (7.0, 6.0), (5.0, 5.0), 1.0),
    ):
        arc = rotation_arrow(start, end, pivot=pivot, layer_id="r", extent=(10.0, 10.0)).path
        middle = arc[len(arc) // 2]
        chord_x = (start[0] + end[0]) / 2
        assert (middle[0] - chord_x) * direction > 0


def test_a_curve_name_sits_below_right_of_its_end_unless_a_line_is_there() -> None:
    from macro_viz.i18n import Labels
    from macro_viz.visuals._theory import curve, theory_canvas

    canvas = theory_canvas(
        10.0,
        10.0,
        labels=Labels(None),
        x_label_id="axis.origin",
        y_label_id="axis.origin",
        title=None,
    )
    canvas.extend(
        curve([(1.0, 8.0), (8.0, 3.0)], layer_id="c", role="macro.curve.primary", label="L")
    )
    label = next(layer for layer in canvas.snapshot().layers if layer.id == "c.label")
    assert label.anchor == "top-left"  # type: ignore[attr-defined]
