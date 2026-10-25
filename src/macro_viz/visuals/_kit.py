"""Renderer-neutral building blocks shared by every macro-viz figure.

A figure is a list of public MosaicKit layers on a ``Canvas``. This module holds the parts
every figure needs: the canvas that applies the label-group nudges of the configuration,
axes with arrowheads and their titles. It names no colour, font,
or size: those come from the theme roles of ``macro_viz.themes`` and the configuration.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import replace
from typing import Any

from mosaickit import (
    ArrowPlacement,
    ArrowStyle,
    Canvas,
    CanvasSpec,
    Layer,
    PathLayer,
    Stroke,
    TextLayer,
)
from mosaickit.styles.nudge import Nudge

from macro_viz.config import active_config
from macro_viz.label_groups import label_group

TITLE_GAP = 6.0
"""Gap between an arrow tip and its axis title, in points."""


class MacroCanvas(Canvas):
    """A MosaicKit canvas that moves each label by its group's default nudge."""

    def __init__(self, *args: Any, label_nudges: Mapping[str, Nudge] | None = None, **kwargs: Any):
        self._label_nudges = dict(label_nudges or {})
        super().__init__(*args, **kwargs)

    def _nudged(self, layer: Layer) -> Layer:
        group = label_group(layer)
        nudge = self._label_nudges.get(group) if group else None
        if nudge is None or not hasattr(layer, "nudge"):
            return layer
        current: Nudge | None = getattr(layer, "nudge", None)
        if current is not None:
            nudge = Nudge(current.dx + nudge.dx, current.dy + nudge.dy)
        return replace(layer, nudge=nudge)  # type: ignore[call-arg]

    def add(self, layer: Layer) -> MacroCanvas:
        super().add(self._nudged(layer))
        return self

    def extend(self, layers: Iterable[Layer]) -> MacroCanvas:
        super().extend([self._nudged(layer) for layer in layers])
        return self


def new_canvas(spec: CanvasSpec) -> MacroCanvas:
    """Create a canvas with the active macro-viz MosaicKit configuration."""
    settings = active_config().settings
    return MacroCanvas(spec, config=settings.mosaickit_config(), label_nudges=settings.label_nudges)


def canvas_spec(
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    *,
    width: float,
    height: float,
    title: str | None,
) -> CanvasSpec:
    """A canvas whose axis titles are drawn by ``axes_layers``, not by the renderer."""
    return CanvasSpec(
        x_range=x_range,
        y_range=y_range,
        width=width,
        height=height,
        x_label="",
        y_label="",
        title=title,
    )


def is_symbol(label: str) -> bool:
    """Single letters and ``$...$`` titles are set as math; words stay upright."""
    wrapped = len(label) > 1 and label.startswith("$") and label.endswith("$")
    return wrapped or (len(label) == 1 and label.isalpha())


def axes_layers(
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    *,
    x_label: str | None,
    y_label: str | None,
    origin_label: str | None = None,
) -> list[Layer]:
    """Axes with arrowheads from the lower-left corner, and their titles past the tips.

    A symbol title (``Y``, ``$i$``) sits right of the x arrow; a word ends at the tip, under
    the arrow. ``origin_label`` (usually ``"0"``) is drawn at the corner when given.
    """
    x0, x1 = x_range
    y0, y1 = y_range
    arrow = Stroke(arrow=ArrowStyle.TRIANGLE)
    layers: list[Layer] = [
        PathLayer(
            ((x0, y0), (x1, y0)),
            id="axes.x",
            role="axes",
            stroke=arrow,
            arrow_placement=ArrowPlacement.END,
            clip=False,
        ),
        PathLayer(
            ((x0, y0), (x0, y1)),
            id="axes.y",
            role="axes",
            stroke=arrow,
            arrow_placement=ArrowPlacement.END,
            clip=False,
        ),
    ]
    if y_label:
        layers.append(
            TextLayer(
                (x0, y1),
                y_label,
                id="axes.y.label",
                role="axes",
                anchor="bottom",
                offset=(0, TITLE_GAP),
                math=is_symbol(y_label),
            )
        )
    if x_label:
        symbol = is_symbol(x_label)
        layers.append(
            TextLayer(
                (x1, y0),
                x_label,
                id="axes.x.label",
                role="axes",
                anchor="left" if symbol else "top-right",
                offset=(TITLE_GAP, 0) if symbol else (0, -TITLE_GAP),
                math=symbol,
            )
        )
    if origin_label:
        layers.append(
            TextLayer(
                (x0, y0),
                origin_label,
                id="axes.origin.label",
                role="axes",
                anchor="right",
                offset=(-7, -7),
            )
        )
    return layers
