# mypy: ignore-errors
"""No label of a linked-panel figure touches a curve, link, arrow, dot, tick or another label."""

from __future__ import annotations

import sys
import warnings
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from matplotlib.patches import ConnectionPatch, FancyArrowPatch, PathPatch
from matplotlib.text import Text
from matplotlib.transforms import Bbox
from mosaickit import CanvasGrid

from macro_viz import Config

sys.path.insert(0, str(Path(__file__).parents[1] / "examples" / "scripts"))

import panels_common as presets  # noqa: E402
from common import load_example, load_settings  # noqa: E402

from macro_viz.panels import Mode  # noqa: E402
from macro_viz.visuals import five_panel_canvas, four_panel_canvas  # noqa: E402

EXAMPLES = Path(__file__).parents[1] / "examples"
PIXEL_SLACK = 1.0
"""Pixels a label may come within of a line before it counts as touching."""


@pytest.fixture(autouse=True)
def _settings() -> Iterator[None]:
    load_settings(EXAMPLES / "econ-viz.toml").use()
    yield
    Config.reset()


def _figures() -> dict[str, Callable[[dict[str, object]], CanvasGrid]]:
    def args(data: dict[str, object], name: str) -> dict[str, object]:
        table = data["drawing"]
        assert isinstance(table, dict)
        return {"extent": table["extent"], "width": table["width"]}

    return {
        "money_sras": lambda d: four_panel_canvas(
            presets.money_sas(d),  # type: ignore[arg-type]
            steps=d["money_sas"]["steps"],  # type: ignore[index]
            **args(d, "money_sas"),
        ),
        "money_lras": lambda d: four_panel_canvas(
            presets.money_illusion(d),  # type: ignore[arg-type]
            lras=True,
            ad=False,
            shift_arrows_on=False,
            shifted_sras=False,
            steps=d["money_illusion"]["steps"],  # type: ignore[index]
            hide_ticks=presets.hidden(d, "money_illusion"),  # type: ignore[arg-type]
            **args(d, "money_illusion"),
        ),
        "capital": lambda d: five_panel_canvas(
            presets.capital(d),  # type: ignore[arg-type]
            hide_ticks=presets.hidden(d, "capital"),  # type: ignore[arg-type]
            **args(d, "capital"),
        ),
        "expenditure": lambda d: five_panel_canvas(
            presets.expenditure(d),  # type: ignore[arg-type]
            mode=Mode.DERIVED,
            lras=True,
            shifted_sras=False,
            hide_ticks=presets.hidden(d, "expenditure"),  # type: ignore[arg-type]
            **args(d, "expenditure"),
        ),
    }


def _is_label(gid: str) -> bool:
    return gid.startswith("macro.panels.") and (
        gid.endswith(".label") or ".tick." in gid or ".point." in gid
    )


def collisions(grid: CanvasGrid) -> list[str]:
    """Pairs of labels, or label and line, that touch in the rendered figure."""
    result = grid.render()
    try:
        figure = result.figure
        figure.canvas.draw()  # type: ignore[attr-defined]
        renderer = figure.canvas.get_renderer()  # type: ignore[attr-defined]
        labels: dict[str, Bbox] = {}
        lines: list[tuple[str, object]] = []
        dots: list[tuple[str, tuple[float, float]]] = []
        for ax in result.axes:
            for artist in ax.get_children():
                gid = artist.get_gid() or ""
                if isinstance(artist, Text) and _is_label(gid) and gid.endswith(".label"):
                    bounds = artist.get_window_extent(renderer)
                    # GlyphKit leaves a one-pixel Matplotlib text placeholder when it draws the
                    # real label as glyph paths.  It is not visible and has no usable text box.
                    if bounds.width > 1 or bounds.height > 1:
                        labels[gid] = bounds
                elif isinstance(artist, Text) and ".tick." in gid:
                    labels[gid] = artist.get_window_extent(renderer)
                elif isinstance(artist, PathPatch) and not gid.endswith(".leader"):
                    path = artist.get_transform().transform_path(artist.get_path())
                    lines.append((gid, path))
                elif isinstance(artist, FancyArrowPatch):
                    lines.append(("arrow", artist.get_path()))
                elif ".point." in gid and hasattr(artist, "get_offsets"):
                    for x, y in artist.get_transform().transform(artist.get_offsets()):
                        dots.append((gid, (float(x), float(y))))
        for artist in figure.artists:
            if isinstance(artist, ConnectionPatch):
                lines.append(("link", artist.get_path()))
        found: list[str] = []
        names = sorted(labels)
        for i, a in enumerate(names):
            box = labels[a].expanded(1.0, 1.0)
            box = Bbox.from_extents(
                box.x0 + PIXEL_SLACK,
                box.y0 + PIXEL_SLACK,
                box.x1 - PIXEL_SLACK,
                box.y1 - PIXEL_SLACK,
            )
            for b in names[i + 1 :]:
                if box.overlaps(labels[b]):
                    found.append(f"{a} x {b}")
            for gid, path in lines:
                if path.intersects_bbox(box, filled=False):  # type: ignore[attr-defined]
                    found.append(f"{a} x {gid}")
            for gid, (x, y) in dots:
                if box.x0 <= x <= box.x1 and box.y0 <= y <= box.y1:
                    found.append(f"{a} x {gid}")
        return found
    finally:
        result.close()


@pytest.mark.parametrize("name", ["money_sras", "money_lras", "capital", "expenditure"])
def test_no_label_touches_a_line_dot_or_label(name: str) -> None:
    data = load_example(EXAMPLES / "examples.toml", "panels")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        grid = _figures()[name](data)
        assert collisions(grid) == []
