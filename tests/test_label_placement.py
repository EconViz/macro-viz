# mypy: ignore-errors
"""Curve names stay at their own curve inside the canvas, and placement problems are reported."""

from __future__ import annotations

import sys
import warnings
from collections.abc import Iterator
from pathlib import Path

import pytest
from matplotlib.text import Text
from mosaickit import CanvasSpec, PathLayer, TextLayer

from macro_viz import Config, LabelPlacementWarning
from macro_viz.visuals import _kit
from macro_viz.visuals._labels import LabelSpec

EXAMPLES = Path(__file__).parents[1] / "examples"
sys.path.insert(0, str(EXAMPLES / "scripts"))

import panels_common as presets  # noqa: E402
from common import load_example, load_settings  # noqa: E402

from macro_viz.panels import Mode  # noqa: E402
from macro_viz.visuals import five_panel_canvas  # noqa: E402

LM_IDS = ("lm.0", "lm.1", "lm.2")


@pytest.fixture(autouse=True)
def _settings() -> Iterator[None]:
    load_settings(EXAMPLES / "econ-viz.toml").use()
    yield
    Config.reset()


@pytest.fixture
def placed(monkeypatch: pytest.MonkeyPatch) -> list[_kit.MacroCanvas]:
    """Every MacroCanvas that placed its labels while a figure was built."""
    seen: list[_kit.MacroCanvas] = []
    original = _kit.MacroCanvas._place_labels

    def spy(self: _kit.MacroCanvas) -> None:
        original(self)
        seen.append(self)

    monkeypatch.setattr(_kit.MacroCanvas, "_place_labels", spy)
    return seen


def _expenditure() -> object:
    data = load_example(EXAMPLES / "examples.toml", "panels")
    table = data["drawing"]
    return five_panel_canvas(
        presets.expenditure(data),
        mode=Mode.DERIVED,
        lras=True,
        shifted_sras=False,
        hide_ticks=presets.hidden(data, "expenditure"),
        extent=table["extent"],
        width=table["width"],
    )


def test_three_parallel_lm_names_sit_at_their_own_curve_inside_the_canvas(placed) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", LabelPlacementWarning)
        grid = _expenditure()
        result = grid.render()
    try:
        canvas = next(c for c in placed if any(i.endswith("islm.lm.2") for i in _ids(c)))
        ends = {
            layer.id: layer.path[-1]
            for layer in canvas._placed_scene.layers
            if isinstance(layer, PathLayer) and layer.id.rsplit("islm.", 1)[-1] in LM_IDS
        }
        assert len(ends) == len(LM_IDS)
        figure = result.figure
        figure.canvas.draw()
        renderer = figure.canvas.get_renderer()
        ax = next(
            a
            for a in result.axes
            if any((t.get_gid() or "").endswith("islm.lm.2.label") for t in a.get_children())
        )
        boxes = {}
        for artist in ax.get_children():
            gid = artist.get_gid() or ""
            if isinstance(artist, Text) and gid.endswith(tuple(f"{i}.label" for i in LM_IDS)):
                boxes[gid[: -len(".label")]] = artist.get_window_extent(renderer)
        assert set(boxes) == set(ends)
        frame = figure.bbox
        for gid, box in boxes.items():
            assert box.width > 1, "the name has no measurable box"
            assert frame.x0 <= box.x0 and box.x1 <= frame.x1, gid
            assert frame.y0 <= box.y0 and box.y1 <= frame.y1, gid
            anchors = {i: ax.transData.transform(p) for i, p in ends.items()}
            nearest = min(
                anchors,
                key=lambda i: _distance(box, anchors[i]),
            )
            assert nearest == gid, f"{gid} sits nearest to {nearest}"
        names = sorted(boxes)
        for i, a in enumerate(names):
            for b in names[i + 1 :]:
                assert not boxes[a].overlaps(boxes[b]), f"{a} overlaps {b}"
    finally:
        result.close()


def _ids(canvas: _kit.MacroCanvas) -> list[str]:
    return [layer.id for layer in canvas._placed_scene.layers]


def _distance(box, point) -> float:
    dx = max(box.x0 - point[0], 0.0, point[0] - box.x1)
    dy = max(box.y0 - point[1], 0.0, point[1] - box.y1)
    return (dx * dx + dy * dy) ** 0.5


def _crowded() -> _kit.MacroCanvas:
    """A canvas whose two names must both fit on one short curve end: no room for both."""
    spec = CanvasSpec(width=2.0, height=1.5, x_range=(0.0, 1.0), y_range=(0.0, 1.0))
    canvas = _kit.new_canvas(spec)
    for key in ("a", "b"):
        canvas.add(PathLayer(id=f"c.{key}", path=((0.0, 0.5), (0.5, 0.5)), role="macro.curve"))
        canvas.add_label(
            TextLayer(
                id=f"c.{key}.label",
                position=(0.5, 0.5),
                text="A very long curve name " * 3,
                role="macro.curve",
            ),
            LabelSpec(f"c.{key}"),
        )
    return canvas


def test_placement_warnings_are_raised_and_kept() -> None:
    canvas = _crowded()
    with pytest.warns(LabelPlacementWarning):
        canvas._scene  # noqa: B018 - reading the scene places the labels
    assert canvas.label_warnings
