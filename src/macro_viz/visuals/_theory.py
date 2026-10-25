"""Building blocks of textbook theory diagrams: curves, guides, points, and marks.

Theory diagrams are drawn on a square canvas with arrowed axes from the origin and no tick
numbers; economic values are named by marks on the axes joined to the figure by dotted guides.
Curves are named directly at their right-hand end (no legend); an old position is thin and
dashed. Every function returns public MosaicKit layers with stable ids.
"""

from __future__ import annotations

import string
from collections.abc import Callable, Sequence

from mosaickit import (
    ArrowLayer,
    ArrowStyle,
    AxisMarkLayer,
    Layer,
    MarkerLayer,
    PathLayer,
    PointLabelLayer,
    Stroke,
)

from macro_viz.errors import ValidationError
from macro_viz.i18n import Labels
from macro_viz.visuals._kit import MacroCanvas, axes_layers, canvas_spec, new_canvas

Point = tuple[float, float]

THEORY_SIZE = 6.0
"""Side in inches of a theory canvas; width and height are arguments of every builder."""

DEFAULT_SAMPLES = 60
"""How many points a curve is sampled at when the caller does not say."""

HEADROOM = 0.92
"""Share of an axis a curve may reach, leaving room for its name and the axis arrow."""

SHIFT_BEND = "left"
"""Default side to which a shift arrow bulges, seen from its start."""

BULGE = 0.12
"""Sideways displacement of a shift arrow's middle, as a share of its length."""

ARC_SAMPLES = 16
"""Points along a curved arrow."""

PRIME = "'"
"""The mark appended to a point name for each step beyond the baseline."""

EXTENT = 1.6
"""Default length of the horizontal axis as a multiple of the largest equilibrium value."""


def point_name(index: int, prime: int = 0) -> str:
    """``A``, ``B``, ... followed by ``prime`` primes, as a math label."""
    return f"${string.ascii_uppercase[index]}{PRIME * prime}$"


def primed(label: str, primes: int) -> str:
    """``label`` (``$...$`` math or plain text) with ``primes`` primes after its last symbol."""
    if not primes:
        return label
    mark = PRIME * primes
    return f"{label[:-1]}{mark}$" if label.startswith("$") and label.endswith("$") else label + mark


def sample(
    function: Callable[[float], float], low: float, high: float, samples: int
) -> list[Point]:
    """``samples`` evenly spaced points of ``function`` on ``[low, high]``."""
    if isinstance(samples, bool) or not isinstance(samples, int) or samples < 2:
        raise ValidationError("samples must be an integer of at least 2")
    if not low < high:
        raise ValidationError("a curve needs low < high")
    step = (high - low) / (samples - 1)
    return [(low + k * step, function(low + k * step)) for k in range(samples)]


def _clip(
    start: Point, end: Point, box: tuple[float, float, float, float]
) -> tuple[Point, Point] | None:
    """The part of a segment inside ``box`` = (x0, y0, x1, y1), or None (Liang-Barsky)."""
    (ax, ay), (bx, by) = start, end
    dx, dy = bx - ax, by - ay
    lo, hi = 0.0, 1.0
    for p, q in (
        (-dx, ax - box[0]),
        (dx, box[2] - ax),
        (-dy, ay - box[1]),
        (dy, box[3] - ay),
    ):
        if p == 0:
            if q < 0:
                return None
            continue
        t = q / p
        if p < 0:
            lo = max(lo, t)
        else:
            hi = min(hi, t)
    if lo > hi:
        return None
    return (ax + lo * dx, ay + lo * dy), (ax + hi * dx, ay + hi * dy)


def trim(
    points: Sequence[Point], x_max: float, y_max: float, *, headroom: float = HEADROOM
) -> list[Point]:
    """The part of a polyline inside the plot, short of ``headroom`` of each axis."""
    box = (0.0, 0.0, headroom * x_max, headroom * y_max)
    kept: list[Point] = []
    for start, end in zip(points, points[1:], strict=False):
        clipped = _clip(start, end, box)
        if clipped is None:
            continue
        first, last = clipped
        if not kept or kept[-1] != first:
            kept.append(first)
        kept.append(last)
    if len(kept) < 2:
        raise ValidationError("the curve does not enter the plot")
    return kept


def theory_canvas(
    x_max: float,
    y_max: float,
    *,
    labels: Labels,
    x_label_id: str,
    y_label_id: str,
    title: str | None,
    width: float = THEORY_SIZE,
    height: float = THEORY_SIZE,
) -> MacroCanvas:
    """A canvas with arrowed axes from the origin, symbol titles, and an optional title."""
    if not (x_max > 0 and y_max > 0):
        raise ValidationError("axis lengths must be positive")
    x_range, y_range = (0.0, x_max), (0.0, y_max)
    canvas = new_canvas(canvas_spec(x_range, y_range, width=width, height=height, title=title))
    canvas.extend(
        axes_layers(
            x_range,
            y_range,
            x_label=labels(x_label_id),
            y_label=labels(y_label_id),
            origin_label=labels("axis.origin"),
        )
    )
    return canvas


def curve(
    points: Sequence[Point],
    *,
    layer_id: str,
    role: str,
    label: str | None = None,
    z_index: int = 2,
) -> list[Layer]:
    """A curve and, when ``label`` is given, its name beside the right-hand end."""
    layers: list[Layer] = [PathLayer(tuple(points), id=layer_id, role=role, z_index=z_index)]
    if label:
        end = max(points, key=lambda point: (point[0], point[1]))
        layers.append(
            PointLabelLayer(end, label, id=f"{layer_id}.label", role=role, z_index=z_index + 5)
        )
    return layers


def guide(start: Point, end: Point, *, layer_id: str) -> PathLayer:
    """A dotted guide joining a point to an axis or to another point."""
    return PathLayer((start, end), id=layer_id, role="macro.guide", z_index=1)


def marked_point(
    point: Point, label: str, *, layer_id: str, role: str = "macro.point"
) -> list[Layer]:
    """A dot and its name placed beside it, covering nothing else."""
    return [
        MarkerLayer((point,), id=layer_id, role=role, z_index=6),
        PointLabelLayer(point, label, id=f"{layer_id}.label", role=role, z_index=7),
    ]


def axis_mark(axis: str, value: float, label: str, *, layer_id: str) -> AxisMarkLayer:
    """A symbol at ``value`` on an axis; ``$...$`` text is set as math."""
    is_math = label.startswith("$") and label.endswith("$")
    return AxisMarkLayer(
        axis,
        value,
        label.strip("$") if is_math else label,
        math=is_math,
        id=layer_id,
        role="axes",
    )


def drop_lines(
    point: Point,
    *,
    x_label: str | None,
    y_label: str | None,
    layer_id: str,
) -> list[Layer]:
    """Guides from ``point`` to both axes, each ending in a mark when its label is given."""
    layers: list[Layer] = []
    x, y = point
    if x_label is not None:
        layers.append(guide((x, 0.0), point, layer_id=f"{layer_id}.x.guide"))
        layers.append(axis_mark("x", x, x_label, layer_id=f"{layer_id}.x.mark"))
    if y_label is not None:
        layers.append(guide((0.0, y), point, layer_id=f"{layer_id}.y.guide"))
        layers.append(axis_mark("y", y, y_label, layer_id=f"{layer_id}.y.mark"))
    return layers


def movement(start: Point, end: Point, *, layer_id: str) -> ArrowLayer:
    """A thin dashed arrow showing how something moves."""
    return ArrowLayer(start, end, id=layer_id, role="macro.movement", z_index=5)


def shift_arrow(
    start: Point,
    end: Point,
    *,
    layer_id: str,
    bend: str = SHIFT_BEND,
    bulge: float = BULGE,
    samples: int = ARC_SAMPLES,
    extent: Point = (1.0, 1.0),
) -> PathLayer:
    """A thin curved arrow from ``start`` to ``end`` that bulges to ``bend`` (left or right).

    ``left`` and ``right`` are seen walking from ``start`` to ``end``; ``bulge`` is the
    sideways displacement of the middle as a share of the arrow's length, measured on the
    page: ``extent`` is the length of the two axes, so a flat figure bends as a square one.
    """
    if bend not in ("left", "right"):
        raise ValidationError("bend must be 'left' or 'right'")
    ex, ey = extent
    dx, dy = (end[0] - start[0]) / ex, (end[1] - start[1]) / ey
    side = 1.0 if bend == "left" else -1.0
    control = (
        (start[0] + end[0]) / 2 - side * dy * bulge * 2 * ex,
        (start[1] + end[1]) / 2 + side * dx * bulge * 2 * ey,
    )
    points = []
    for k in range(samples):
        t = k / (samples - 1)
        points.append(
            (
                (1 - t) ** 2 * start[0] + 2 * (1 - t) * t * control[0] + t**2 * end[0],
                (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * control[1] + t**2 * end[1],
            )
        )
    return PathLayer(
        tuple(points),
        id=layer_id,
        role="macro.movement",
        stroke=Stroke(arrow=ArrowStyle.OPEN),
        z_index=5,
        clip=False,
    )


def movement_label(start: Point, end: Point, label: str, *, layer_id: str) -> list[Layer]:
    """A curved shift arrow with its name placed beside its middle, covering nothing else."""
    middle = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
    return [
        shift_arrow(start, end, layer_id=layer_id),
        PointLabelLayer(middle, label, id=f"{layer_id}.label", role="macro.annotation", z_index=7),
    ]
