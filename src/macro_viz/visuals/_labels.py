"""One call places every movable label of a figure: curve names, point labels, tick labels.

The placer is MosaicKit's (``mosaickit.label_scene.place_scene_labels``): it takes the whole
scene (curves, arrows, dots, guides, axis titles, every other text) and chooses all positions
together, so no label depends on the order the others were added in. This module is the one
adapter: it names the side order of each kind of label, measures text in the figure's real
fonts at the size its role draws it in (never shrinking it), and hands the result back as
replacement layers. Whatever the placer cannot solve is reported through ``report``.
"""

from __future__ import annotations

import math
import warnings
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from functools import cache

from mosaickit import Layer, PathLayer, TextLayer
from mosaickit.diagram import (
    DEFAULT_NAME_ORDER,
    RISING_NAME_ORDER,
    TEX_LAYOUT_COMMANDS,
    estimate_text_size,
)
from mosaickit.label_scene import CurveEnd, SceneLabelOptions, curve_end, place_scene_labels
from mosaickit.layout import Rect
from mosaickit.layout.labels import LabelOptions, PlacementWarning

from macro_viz.core.config import active_config
from macro_viz.core.errors import LabelPlacementWarning, ValidationError

Point = tuple[float, float]

POINTS_PER_INCH = 72.0
NAME_SUFFIX = ".label"
"""A curve's name has the id of its curve followed by this."""

LEADER_ROLE = "macro.link.leader"
"""Theme role of a leader: thin and solid, in the manual style."""

CURVE_SIDES = DEFAULT_NAME_ORDER
"""Where the name of a falling or flat curve goes off its end, first choice first."""

RISING_SIDES = RISING_NAME_ORDER
"""The same for a rising curve: above and right of its upper end."""

PANEL_CURVE_SIDES = (
    "right",
    "upper-right",
    "lower-right",
    "above",
    "below",
    "upper-left",
    "left",
    "lower-left",
)
"""The same for a curve of a linked panel, whose end usually sits beside empty room."""

POINT_SIDES = (
    "upper-right",
    "lower-right",
    "upper-left",
    "lower-left",
    "right",
    "left",
    "above",
    "below",
)
"""Where the name of a dot goes, first choice first."""

TICK_SIDES = {
    "x": ("below", "lower-left", "lower-right"),
    "y": ("left", "upper-left", "lower-left"),
}
"""Where a tick label goes off its axis, first choice first, by the axis it is on: straight out,
then leaning away from a crowded neighbour, always on the outer side of the axis."""

UPPER_RIGHT_TAIL_LABELS = frozenset(("lm", "sras"))
"""Curve families that rise to the upper right: named above-right of their top end."""

FAMILY_ENDS: Mapping[str, CurveEnd] = {family: "top" for family in UPPER_RIGHT_TAIL_LABELS}
"""Which end of its curve a family's name belongs to; every other family uses the rightmost."""

DEFAULT_END: CurveEnd = "rightmost"
PATH_TOLERANCE = 0.25
"""Points a curve may be simplified by when labels are placed around it (the drawn curve is
untouched): finer than a pixel, but a long smooth curve then costs a handful of segments."""

MIN_THINNED_POINTS = 8
"""Paths with fewer points are left as they are."""

SEARCH_RINGS = 6
"""Rings of free positions tried around an anchor: enough for every figure here, and keeps the
search (the cost of building a figure) short."""

SEARCH_DIRECTIONS = 12
"""Compass directions tried on each ring."""

LABEL_OPTIONS = LabelOptions(rings=SEARCH_RINGS, ring_directions=SEARCH_DIRECTIONS)
"""The placer's distances (gap, clearance, leaders ...) are MosaicKit's documented defaults."""


@dataclass(frozen=True, slots=True)
class LabelSpec:
    """A movable text layer: what it names (``owner``, a layer id) and its side order.

    ``sides`` of ``None`` lets a curve name pick by its curve's slope.
    """

    owner: str | None = None
    sides: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class Frame:
    """The drawing area: ``bounds`` in points and the points per data unit along each axis."""

    bounds: Rect
    scale: Point


def family_end(path: Sequence[Point], family: str | None = None) -> Point:
    """The point of ``path`` the name of a curve of ``family`` belongs to."""
    return curve_end(path, FAMILY_ENDS.get(family or "", DEFAULT_END))


def rises(path: Sequence[Point]) -> bool:
    """Whether the curve is higher at its right end than at its left end."""
    left, right = min(path, key=lambda p: p[0]), max(path, key=lambda p: p[0])
    return right[1] > left[1]


AXES_RECT = (0.125, 0.9, 0.11, 0.88)
"""Left, right, bottom and top of a single canvas' axes as shares of the page.

These are Matplotlib's default ``figure.subplot.*`` margins, which MosaicKit's renderer uses for
a lone canvas; the engine offers no renderer-independent way to read them.
"""


def figure_frame(x_range: Point, y_range: Point, width: float, height: float) -> Frame:
    """The frame of a single canvas of ``width`` x ``height`` inches.

    The axes fill the share Matplotlib gives them; names may also use the margin on their
    right (where the x-axis title sits), as the figure is saved with it.
    """
    page = (width * POINTS_PER_INCH, height * POINTS_PER_INCH)
    left, right, bottom, top = AXES_RECT
    return axes_frame(
        x_range,
        y_range,
        (page[0] * (right - left), page[1] * (top - bottom)),
        right_margin=page[0] * (1 - right),
    )


def axes_frame(x_range: Point, y_range: Point, size: Point, *, right_margin: float = 0.0) -> Frame:
    """The frame of axes ``size`` points across that show ``x_range`` and ``y_range``."""
    scale = (size[0] / (x_range[1] - x_range[0]), size[1] / (y_range[1] - y_range[0]))
    bounds = Rect(
        x_range[0] * scale[0],
        y_range[0] * scale[1],
        x_range[1] * scale[0] + right_margin,
        y_range[1] * scale[1],
    )
    return Frame(bounds, scale)


def as_drawn(text: str, math: bool) -> str:
    """``text`` as the renderer sets it: math text without ``$`` gets them."""
    return f"${text}$" if math and not (text.startswith("$") and text.endswith("$")) else text


@cache
def _measurer(size: float, weight: object, font: object, math_font: object, text_fonts: object):  # type: ignore[no-untyped-def]
    from mosaickit.rendering.matplotlib import text_measurer  # needs the rendering extras

    return text_measurer(
        size,
        weight=weight,  # type: ignore[arg-type]
        font=font,  # type: ignore[arg-type]
        math_font=math_font,  # type: ignore[arg-type]
        text_fonts=text_fonts,  # type: ignore[arg-type]
    )


class _Metrics:
    """Sizes every text of a figure as its role draws it: real extents, else an estimate."""

    def __init__(self, layers: Sequence[Layer], theme: object, config: object) -> None:
        self._found: dict[str, tuple[float, object, object, bool]] = {}
        self._config = config
        self._estimating = False
        for layer in layers:
            if isinstance(layer, TextLayer) and isinstance(layer.text, str):
                self._register(layer, theme)

    def _register(self, layer: TextLayer, theme: object) -> None:
        style = theme.resolve(layer.role, fallback_category=layer.fallback_category).text  # type: ignore[attr-defined]
        if layer.style is not None:
            style = layer.style.merged_over(style)
        entry = (float(style.size), style.weight, style.font, layer.math)
        known = self._found.get(layer.text)
        if known is None or entry[0] > known[0]:
            self._found[layer.text] = entry

    def __call__(self, text: str) -> Point:
        size, weight, font, math = self._found.get(text, (0.0, None, None, False))
        drawn = as_drawn(text, math)
        if not self._estimating:
            config = self._config
            try:
                measure = _measurer(size, weight, font, config.math_font, config.fonts)  # type: ignore[attr-defined]
                return tuple(measure(drawn))
            except ImportError:  # nothing can draw this figure: its text is only estimated
                self._estimating = True
            except Exception as error:
                self._estimating = True
                warnings.warn(
                    LabelPlacementWarning(f"cannot measure text ({error}); sizes are estimates"),
                    stacklevel=2,
                )
        return estimate_text_size(drawn, size, strip_commands=TEX_LAYOUT_COMMANDS)


def report(found: Sequence[PlacementWarning], figure: str = "figure") -> None:
    """Surface every label the placer could not place free of collisions, loudly."""
    for item in found:
        detail = f": {item.detail}" if item.detail else ""
        warnings.warn(
            LabelPlacementWarning(f"{figure}: label {item.label_id!r} {item.reason}{detail}"),
            stacklevel=3,
        )


def _sides(spec: LabelSpec, owner: Layer | None) -> tuple[str, ...]:
    if spec.sides is not None:
        return spec.sides
    path = getattr(owner, "path", None)
    return RISING_SIDES if path is not None and len(path) > 1 and rises(path) else CURVE_SIDES


def _thinned(layer: Layer, scale: Point) -> Layer:
    """``layer`` with the points a polyline does not need dropped (within ``PATH_TOLERANCE``)."""
    if not isinstance(layer, PathLayer) or len(layer.path) < MIN_THINNED_POINTS:
        return layer
    pts = [(x * scale[0], y * scale[1]) for x, y in layer.path]
    keep = {0, len(pts) - 1}
    todo = [(0, len(pts) - 1)]
    while todo:
        a, b = todo.pop()
        (ax, ay), (bx, by) = pts[a], pts[b]
        length = math.hypot(bx - ax, by - ay) or 1.0
        far, at = 0.0, a
        for i in range(a + 1, b):
            d = abs((bx - ax) * (ay - pts[i][1]) - (ax - pts[i][0]) * (by - ay)) / length
            if d > far:
                far, at = d, i
        if far > PATH_TOLERANCE:
            keep.add(at)
            todo += [(a, at), (at, b)]
    return replace(layer, path=tuple(layer.path[i] for i in sorted(keep)))


def place_canvas_labels(
    layers: Sequence[Layer],
    specs: Mapping[str, LabelSpec],
    frame: Frame,
    *,
    theme: object,
    config: object,
    options: LabelOptions = LABEL_OPTIONS,
) -> tuple[dict[str, Layer], tuple[PlacementWarning, ...]]:
    """Replacement layers (by id, leaders included) for the labels of ``specs``.

    ``layers`` are all the figure's layers; each label's anchor is its own ``position``.
    """
    by_id = {layer.id: layer for layer in layers}
    movable = [by_id[i] for i in specs if isinstance(by_id.get(i), TextLayer)]
    if not movable:
        return {}, ()
    owners: dict[str, str] = {}
    sides: dict[str, tuple[str, ...]] = {}
    for layer in movable:
        spec = specs[layer.id]
        owner = by_id.get(spec.owner) if spec.owner is not None else None
        if spec.owner is not None:
            if owner is None:
                raise ValidationError(
                    f"label {layer.id!r} names {spec.owner!r}, which is not drawn"
                )
            owners[layer.id] = spec.owner
        sides[layer.id] = _sides(spec, owner)
    radius = active_config().settings.options.point_size ** 0.5 / 2
    # The first ring is far enough from an anchor for its own dot (and curve) to keep the
    # clearance every other line has.
    spaced = replace(
        options,
        gap=max(options.gap, radius + options.clearance),
        own_clearance=max(options.own_clearance, options.clearance),
    )
    scene = SceneLabelOptions(marker_radius=radius, leader_role=LEADER_ROLE, placement=spaced)
    placed, result = place_scene_labels(
        [layer if layer.id in specs else _thinned(layer, frame.scale) for layer in layers],
        movable,  # type: ignore[arg-type]
        frame.bounds,
        frame.scale,
        _Metrics(layers, theme, config),
        scene,
        sides=sides,
        owners=owners,
    )
    return {
        layer.id: layer for layer in placed if layer.id in specs or layer.id not in by_id
    }, result.warnings
