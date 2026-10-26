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
    ArrowLayer,
    ArrowPlacement,
    ArrowStyle,
    Canvas,
    CanvasSpec,
    Layer,
    MarkerLayer,
    PathLayer,
    Stroke,
    TextLayer,
)
from mosaickit.styles.nudge import Nudge

from macro_viz.config import active_config
from macro_viz.label_groups import label_group
from macro_viz.visuals._placement import PlacementOptions, Scene, place, text_box

PLOT_SHARE = 0.78
"""Share of a canvas side taken by the axes; the rest is margin for axis marks and titles."""

CURVE_NAME_ORDER = (
    "lower-right",
    "upper-left",
    "lower-left",
    "upper-right",
    "right",
    "left",
    "above",
    "below",
)
"""Where a curve's name goes off its end, first choice first."""

RISING_NAME_ORDER = (
    "upper-right",
    "right",
    "lower-right",
    "above",
    "upper-left",
    "lower-left",
    "left",
    "below",
)
"""The same, for a rising curve whose name sits above its end."""

CURVE_NAME_CLEARANCE = 3.5
"""Free space in points kept between a curve name and any line or other name."""

CURVE_NAME_WIDTH = 0.8
"""Average character width in em assumed when placing curve names (a margin over the real one)."""

TITLE_GAP = 6.0
"""Gap between an arrow tip and its axis title, in points."""


class MacroCanvas(Canvas):
    """A MosaicKit canvas that moves each label by its group's default nudge."""

    def __init__(self, *args: Any, label_nudges: Mapping[str, Nudge] | None = None, **kwargs: Any):
        self._label_nudges = dict(label_nudges or {})
        self._spec: CanvasSpec | None = args[0] if args else kwargs.get("spec")
        self.rising_names_above = False
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
        self._place_curve_names()
        return self

    def extend(self, layers: Iterable[Layer]) -> MacroCanvas:
        super().extend([self._nudged(layer) for layer in layers])
        self._place_curve_names()
        return self

    def _place_curve_names(self) -> None:
        """Put each curve's name at the first free diagonal off its end, clear of every line.

        Curves and arrows may be added after a name, so every name is placed again, in the
        order the curves were added, whenever the figure changes.
        """
        if self._spec is None:
            return
        layers: list[Any] = list(self.snapshot().layers)
        names: list[Any] = [layer for layer in layers if _is_curve_name(layer)]
        if not names:
            return
        options = active_config().settings.options
        size = options.label_size * options.text_scale
        placement = PlacementOptions(
            clearance=CURVE_NAME_CLEARANCE, character_width=CURVE_NAME_WIDTH
        )
        scene, scale = _scene(self._spec, layers, options.point_size**0.5)
        for name in names:
            curve = next((p for p in layers if p.id == name.id[: -len(".label")]), None)
            if curve is None:
                continue
            end = max(curve.path, key=lambda point: (point[0], point[1]))
            anchor = (end[0] * scale[0], end[1] * scale[1])
            box_size = text_box(str(name.text), size, placement)
            rising = len(curve.path) > 1 and curve.path[-1][1] > curve.path[0][1]
            order = RISING_NAME_ORDER if self.rising_names_above and rising else CURVE_NAME_ORDER
            placed = place(anchor, box_size, scene, placement, order)
            scene.boxes.append(placed.box)
            side = placed.anchor
            moved = replace(name, anchor=side, offset=_offset(placed.position, anchor))
            self.remove(name.id)
            super().add(moved)


def _is_curve_name(layer: Layer) -> bool:
    return (
        isinstance(layer, TextLayer)
        and layer.id.endswith(".label")
        # Linked panels already place names against the complete per-panel scene. Re-running
        # the generic placer loses that scene and can push a name into a neighbouring panel.
        and not layer.role.startswith("macro.curve.panel")
        and (layer.role == "macro.curve" or layer.role.startswith("macro.curve."))
    )


def _scene(spec: CanvasSpec, layers: list[Layer], dot_radius: float):  # type: ignore[no-untyped-def]
    """The lines and dots of the figure in points on the axes, and the points per data unit."""
    x0, x1 = spec.x_range
    y0, y1 = spec.y_range
    width, height = spec.width * 72.0 * PLOT_SHARE, spec.height * 72.0 * PLOT_SHARE
    scale = (width / (x1 - x0), height / (y1 - y0))
    scene = Scene(limits=(0.0, 0.0, width * 1.12, height), dot_radius=dot_radius)
    for layer in layers:
        if isinstance(layer, PathLayer):
            scene.add_polyline([(x * scale[0], y * scale[1]) for x, y in layer.path])
        elif isinstance(layer, ArrowLayer):
            scene.add_polyline([(x * scale[0], y * scale[1]) for x, y in (layer.start, layer.end)])
        elif isinstance(layer, MarkerLayer):
            scene.dots.extend((x * scale[0], y * scale[1]) for x, y in layer.points)
    return scene, scale


def _offset(position: tuple[float, float], anchor: tuple[float, float]):  # type: ignore[no-untyped-def]
    """The offset in points from the curve's end to where the text anchor sits."""
    return (position[0] - anchor[0], position[1] - anchor[1])


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
