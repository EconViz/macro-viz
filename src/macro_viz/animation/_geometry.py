"""The world-to-page mapping of a canvas and the box tests of label placement."""

from __future__ import annotations

from dataclasses import dataclass

from mosaickit import (
    Canvas,
)

from macro_viz.animation._preset import POINTS_PER_INCH, SEGMENT_SAMPLES


@dataclass(frozen=True)
class _Geometry:
    """Where the axes sit in an animated SVG, whose world units are points.

    KineticKit scales a scene uniformly, so the figure is laid out in points (``width`` by
    ``height``) and each axis is mapped linearly onto the plot area inside the margins.
    """

    x_range: tuple[float, float]
    y_range: tuple[float, float]
    width: float
    height: float
    margin: tuple[float, float, float, float]

    def world(self, point: tuple[float, float]) -> tuple[float, float]:
        left, bottom, right, top = self.margin
        (x0, x1), (y0, y1) = self.x_range, self.y_range
        return (
            left + (point[0] - x0) / (x1 - x0) * (self.width - left - right),
            bottom + (point[1] - y0) / (y1 - y0) * (self.height - top - bottom),
        )

    @property
    def plot(self) -> tuple[float, float, float, float]:
        left, bottom, right, top = self.margin
        return (left, bottom, self.width - right, self.height - top)


def _geometry(canvas: Canvas, margin: tuple[float, float, float, float]) -> _Geometry:
    spec = canvas.spec
    return _Geometry(
        spec.x_range,
        spec.y_range,
        spec.width * POINTS_PER_INCH,
        spec.height * POINTS_PER_INCH,
        margin,
    )


def _overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> int:
    return int(a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3])


def _segment_hits_box(
    start: tuple[float, float], end: tuple[float, float], box: tuple[float, float, float, float]
) -> int:
    """Whether the segment passes through the rectangle (sampled along its length)."""
    for k in range(SEGMENT_SAMPLES + 1):
        x = start[0] + (end[0] - start[0]) * k / SEGMENT_SAMPLES
        y = start[1] + (end[1] - start[1]) * k / SEGMENT_SAMPLES
        if box[0] <= x <= box[2] and box[1] <= y <= box[3]:
            return 1
    return 0
