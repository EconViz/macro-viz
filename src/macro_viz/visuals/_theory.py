"""Building blocks of textbook theory diagrams: curves, guides, points, and marks.

Theory diagrams are drawn on a square canvas with arrowed axes from the origin and no tick
numbers; economic values are named by marks on the axes joined to the figure by dotted guides.
Curves are named directly at their right-hand end (no legend); an old position is thin and
solid. Every function returns public MosaicKit layers with stable ids.
"""

from __future__ import annotations

import string
from collections.abc import Callable, Sequence

from bezierkit import Point as BezierPoint
from bezierkit.construction import RotationConnector
from mosaickit import (
    ArrowLayer,
    ArrowStyle,
    AxisMarkLayer,
    Layer,
    MarkerLayer,
    PathLayer,
    PointLabelLayer,
    Stroke,
    TextLayer,
)
from mosaickit.layout import clip_polyline

from macro_viz.errors import ValidationError
from macro_viz.i18n import Labels
from macro_viz.visuals._kit import MacroCanvas, axes_layers, canvas_spec, new_canvas
from macro_viz.visuals._labels import family_end

Point = tuple[float, float]

THEORY_SIZE = 6.0
"""Side in inches of a theory canvas; width and height are arguments of every builder."""

DEFAULT_SAMPLES = 60
"""How many points a curve is sampled at when the caller does not say."""

HEADROOM = 0.92
"""Share of an axis a curve may reach, leaving room for its name and the axis arrow."""

PRIME = "'"
"""The mark appended to a point name for each step beyond the baseline."""

EXTENT = 1.6
"""Default length of the horizontal axis as a multiple of the largest equilibrium value."""

CENTERED_EXTENT = 2.0
"""Axis multiple that places an unshifted equilibrium halfway along an origin-based axis."""

ROTATION_SAMPLES = 48
"""Sampling resolution for BezierKit rotation markers."""


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


def trim(
    points: Sequence[Point],
    x_max: float,
    y_max: float,
    *,
    headroom: float = HEADROOM,
    floor: float = 0.0,
) -> list[Point]:
    """The part of a polyline inside the plot, short of ``headroom`` of each axis.

    ``floor`` (a share of the vertical axis) also cuts off the part below it, so a falling line
    does not end on the axis where its name would collide with the axis marks.
    """
    kept = clip_polyline(points, (0.0, headroom * x_max), (floor * y_max, headroom * y_max))
    if len(kept) < 2:
        raise ValidationError("the curve does not enter the plot")
    return list(kept)


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
    """A curve and, when ``label`` is given, its name at the right-hand end.

    The name is placed with every other label, clear of every line (see ``MacroCanvas``).
    """
    layers: list[Layer] = [PathLayer(tuple(points), id=layer_id, role=role, z_index=z_index)]
    if label:
        layers.append(_end_label(label, family_end(points), layer_id, role, z_index + 5))
    return layers


def _end_label(label: str, end: Point, layer_id: str, role: str, z_index: int) -> TextLayer:
    """The name of a curve at its end; ``MacroCanvas`` places it."""
    return TextLayer(end, label, id=f"{layer_id}.label", role=role, z_index=z_index)


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
    """A thin solid arrow showing how something moves."""
    return ArrowLayer(start, end, id=layer_id, role="macro.movement", z_index=5)


def shift_arrow(start: Point, end: Point, *, layer_id: str) -> ArrowLayer:
    """A straight arrow for a parallel shift.

    It starts at the old equilibrium and ends on the new curve, so it is horizontal for a
    sideways shift and vertical for a shift up or down.
    """
    return movement(start, end, layer_id=layer_id)


def rotation_arrow(
    start: Point,
    end: Point,
    *,
    pivot: Point,
    layer_id: str,
    extent: Point = (1.0, 1.0),
) -> PathLayer:
    """An angle-derived rotation arrow whose opening faces the vertical centreline.

    A marker left of the centreline bows left and therefore opens right; one on the right bows
    right and opens left. ``extent`` normalises the two axes so the bend looks the same in flat
    and square figures.
    """
    if extent[0] <= 0 or extent[1] <= 0:
        raise ValidationError("rotation arrow extent must be positive")
    normalised_start = (start[0] / extent[0], start[1] / extent[1])
    normalised_end = (end[0] / extent[0], end[1] / extent[1])
    normalised_pivot = (pivot[0] / extent[0], pivot[1] / extent[1])
    connector = RotationConnector(
        BezierPoint(*normalised_start),
        BezierPoint(*normalised_end),
        BezierPoint(*normalised_pivot),
    ).build()
    parameters = [index / (ROTATION_SAMPLES - 1) for index in range(ROTATION_SAMPLES)]
    points = tuple(
        (point.x * extent[0], point.y * extent[1]) for point in connector.at_many(parameters)
    )
    return PathLayer(
        points,
        id=layer_id,
        role="macro.movement",
        stroke=Stroke(arrow=ArrowStyle.OPEN),
        z_index=5,
        clip=False,
    )


def movement_label(start: Point, end: Point, label: str, *, layer_id: str) -> list[Layer]:
    """A straight shift arrow with its name placed beside its middle, covering nothing else."""
    middle = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
    horizontal = abs(end[0] - start[0]) >= abs(end[1] - start[1])
    anchor = "bottom" if horizontal else "left"
    offset = (0, 4) if horizontal else (4, 0)
    return [
        shift_arrow(start, end, layer_id=layer_id),
        TextLayer(
            middle,
            label,
            id=f"{layer_id}.label",
            role="macro.annotation",
            anchor=anchor,
            offset=offset,
            z_index=7,
        ),
    ]
