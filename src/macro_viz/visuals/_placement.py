"""Where a label goes: beside its anchor in the emptiest direction, else on a thin leader.

Everything is computed in points on the panel (data coordinates are scaled by the size of the
axes), from the curves, links, arrows, dots, axes, tick labels and labels already placed. A label
takes the first free spot of an ordered list of candidates around its anchor; if none is free it
moves outward in steps and is joined to its anchor by a leader line. No position is typed in:
``PlacementOptions`` holds the distances and the text-size estimate.
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass, field

Point = tuple[float, float]
Box = tuple[float, float, float, float]
"""``(x0, y0, x1, y1)`` in points."""

MARKUP = re.compile(r"[$\\{}^_,]")


@dataclass(frozen=True, slots=True)
class PlacementOptions:
    """Distances in points and the text-size estimate used to place labels."""

    gap: float = 5.0
    """Free space between a label and its anchor."""
    clearance: float = 3.0
    """Free space kept between a label and any line."""
    step: float = 14.0
    """Distance by which a label moves outward for each ring of the leader search."""
    rings: int = 8
    """How many rings the leader search tries."""
    character_width: float = 0.6
    """Average width of a character, in em, of the label font."""
    line_height: float = 1.25
    """Height of a line of text, in em."""
    directions: int = 16
    """How many directions each ring tries."""


@dataclass(frozen=True, slots=True)
class Placed:
    """A placed label: where its box sits, and the leader to its anchor if it needed one."""

    box: Box
    anchor: str
    position: Point
    leader: tuple[Point, Point] | None


@dataclass(slots=True)
class Scene:
    """What is already on a panel, in points: segments, boxes and dots."""

    segments: list[tuple[Point, Point]] = field(default_factory=list)
    boxes: list[Box] = field(default_factory=list)
    dots: list[Point] = field(default_factory=list)
    limits: Box = (0.0, 0.0, 0.0, 0.0)
    dot_radius: float = 4.0

    def add_polyline(self, points: Sequence[Point]) -> None:
        self.segments.extend(zip(points, points[1:], strict=False))


def text_box(text: str, size: float, o: PlacementOptions) -> tuple[float, float]:
    """Estimated ``(width, height)`` in points of ``text`` set at ``size`` points."""
    glyphs = len(MARKUP.sub("", text))
    return o.character_width * size * glyphs, o.line_height * size


def _hits_segment(box: Box, a: Point, b: Point) -> bool:
    x0, y0, x1, y1 = box
    (ax, ay), (bx, by) = a, b
    if max(ax, bx) < x0 or min(ax, bx) > x1 or max(ay, by) < y0 or min(ay, by) > y1:
        return False
    dx, dy = bx - ax, by - ay
    lo, hi = 0.0, 1.0
    for p, q in ((-dx, ax - x0), (dx, x1 - ax), (-dy, ay - y0), (dy, y1 - ay)):
        if p == 0:
            if q < 0:
                return False
            continue
        t = q / p
        if p < 0:
            lo = max(lo, t)
        else:
            hi = min(hi, t)
    return lo <= hi


def _overlap(a: Box, b: Box) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _grow(box: Box, by: float) -> Box:
    return (box[0] - by, box[1] - by, box[2] + by, box[3] + by)


def is_free(box: Box, scene: Scene, o: PlacementOptions, ignore: Sequence[Point] = ()) -> bool:
    """Whether ``box`` is inside the panel and touches no segment, box or dot of ``scene``."""
    x0, y0, x1, y1 = scene.limits
    if box[0] < x0 or box[1] < y0 or box[2] > x1 or box[3] > y1:
        return False
    padded = _grow(box, o.clearance)
    if any(_hits_segment(padded, a, b) for a, b in scene.segments):
        return False
    if any(_overlap(padded, other) for other in scene.boxes):
        return False
    r = scene.dot_radius
    for x, y in scene.dots:
        if (x, y) in ignore:
            continue
        if padded[0] - r <= x <= padded[2] + r and padded[1] - r <= y <= padded[3] + r:
            return False
    return True


TEXT_ANCHOR = {
    "right": "left",
    "left": "right",
    "above": "bottom",
    "below": "top",
    "upper-right": "bottom-left",
    "lower-right": "top-left",
    "upper-left": "bottom-right",
    "lower-left": "top-right",
}
"""The mosaickit ``TextLayer`` anchor that puts the text on that side of its position."""

POINT_ORDER = (
    "upper-right",
    "lower-right",
    "upper-left",
    "lower-left",
    "right",
    "left",
    "above",
    "below",
)
CURVE_ORDER = ("right", "upper-right", "lower-right", "above", "below", "left")


def _box_at(point: Point, side: str, size: tuple[float, float], gap: float) -> tuple[Box, Point]:
    """The box on ``side`` of ``point`` and the point where its text anchor sits."""
    w, h = size
    px, py = point
    d = gap * 0.75 if "-" in side else gap
    horizontal = {"right": 1, "upper-right": 1, "lower-right": 1}.get(side, 0)
    if side in ("left", "upper-left", "lower-left"):
        horizontal = -1
    vertical = 1 if side in ("above", "upper-right", "upper-left") else 0
    if side in ("below", "lower-right", "lower-left"):
        vertical = -1
    ax = px + horizontal * d
    ay = py + vertical * d
    x0 = ax if horizontal > 0 else ax - w if horizontal < 0 else ax - w / 2
    y0 = ay if vertical > 0 else ay - h if vertical < 0 else ay - h / 2
    return (x0, y0, x0 + w, y0 + h), (ax, ay)


def place(
    anchor: Point,
    size: tuple[float, float],
    scene: Scene,
    o: PlacementOptions,
    order: Sequence[str],
    *,
    gap: float | None = None,
    ignore: Sequence[Point] = (),
) -> Placed:
    """The first free spot for a label of ``size`` around ``anchor``.

    Tries ``order`` beside the anchor, then rings of increasing distance in ``o.directions``
    directions with a leader from the anchor to the box. Falls back to the first candidate when
    nothing is free.
    """
    distance = o.gap if gap is None else gap
    for side in order:
        box, at = _box_at(anchor, side, size, distance)
        if is_free(box, scene, o, ignore):
            return Placed(box, TEXT_ANCHOR[side], at, None)
    for ring in range(1, o.rings + 1):
        radius = distance + ring * o.step
        for k in range(o.directions):
            angle = 2 * math.pi * k / o.directions
            centre = (anchor[0] + radius * math.cos(angle), anchor[1] + radius * math.sin(angle))
            w, h = size
            box = (centre[0] - w / 2, centre[1] - h / 2, centre[0] + w / 2, centre[1] + h / 2)
            if not is_free(box, scene, o, ignore):
                continue
            edge = _nearest_on_box(box, anchor)
            start = _toward(anchor, edge, distance - 1.0)
            if _leader_free(start, edge, scene, ignore):
                return Placed(box, "center", centre, (start, edge))
    box, at = _box_at(anchor, order[0], size, distance)
    return Placed(box, TEXT_ANCHOR[order[0]], at, None)


def _nearest_on_box(box: Box, p: Point) -> Point:
    return (min(max(p[0], box[0]), box[2]), min(max(p[1], box[1]), box[3]))


def _toward(a: Point, b: Point, length: float) -> Point:
    d = math.dist(a, b)
    if d == 0:
        return a
    t = min(length / d, 1.0)
    return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))


def _leader_free(a: Point, b: Point, scene: Scene, ignore: Sequence[Point]) -> bool:
    """A leader may cross lines but not another label or tick."""
    return not any(_hits_segment(box, a, b) for box in scene.boxes)


def _closest(p: Point, a: Point, b: Point) -> Point:
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = dx * dx + dy * dy
    t = 0.0 if n == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / n))
    return (a[0] + t * dx, a[1] + t * dy)


def _segments_cross(a: Point, b: Point, c: Point, d: Point) -> bool:
    def orient(p: Point, q: Point, r: Point) -> float:
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    return (orient(a, b, c) * orient(a, b, d) < 0) and (orient(c, d, a) * orient(c, d, b) < 0)
