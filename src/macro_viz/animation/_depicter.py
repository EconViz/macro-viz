"""Maps MosaicKit layers to KineticKit nodes."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from mosaickit import (
    ArrowLayer,
    AxisMarkLayer,
    Canvas,
    FillLayer,
    Layer,
    MarkerLayer,
    PathLayer,
    PointLabelLayer,
    TextLayer,
)
from mosaickit.themes import StyleBundle

if TYPE_CHECKING:  # pragma: no cover
    from kinetickit.scene.node import Node

from macro_viz.animation._geometry import _Geometry, _overlap, _segment_hits_box
from macro_viz.animation._preset import (
    ARROW_HEAD_HALF_WIDTH,
    ARROW_HEAD_LENGTH,
    BASELINE_SHARE,
    DASH_PATTERNS,
    DEFAULT_MARKER_AREA,
    DEFAULT_TEXT_SIZE,
    LABEL_CORNERS,
    LABEL_GAP,
)
from macro_viz.animation._typography import _horizontal, _plain, _vertical


class _Depicter:
    """Maps MosaicKit layers to KineticKit nodes with the layers' ids."""

    def __init__(self, canvas: Canvas, geometry: _Geometry, typography: Any) -> None:
        from kinetickit.geometry.two_d import Path2D, Vec2
        from kinetickit.interpolation import Color
        from kinetickit.scene import PathNode2D, Point2D, Shape2D, Text2D

        self._kk: dict[str, Any] = {
            "Path2D": Path2D,
            "Vec2": Vec2,
            "Color": Color,
            "PathNode2D": PathNode2D,
            "Point2D": Point2D,
            "Shape2D": Shape2D,
            "Text2D": Text2D,
        }
        self.theme = canvas.theme
        self.geometry = geometry
        self.typography = typography
        self.spec = canvas.spec
        self.segments = [
            (geometry.world(a), geometry.world(b))
            for layer in canvas.snapshot().layers
            if isinstance(layer, PathLayer) and layer.role.startswith("macro.")
            for a, b in zip(layer.path, layer.path[1:], strict=False)
        ]
        self.placed: list[tuple[float, float, float, float]] = []

    def bundle(self, layer: Layer) -> StyleBundle:
        return self.theme.resolve(layer.role, fallback_category=layer.fallback_category)

    def color(self, value: Any, opacity: float | None = None) -> Any:
        alpha = value.alpha * (1.0 if opacity is None else opacity)
        return self._kk["Color"](value.red, value.green, value.blue, alpha)

    def stroke(self, layer: Layer) -> Any:
        bundle = self.bundle(layer).stroke
        own = getattr(layer, "stroke", None)
        return own.merged_over(bundle) if own is not None and bundle is not None else own or bundle

    def dash(self, stroke: Any) -> tuple[float, ...]:
        width = stroke.width or 1.0
        pattern = DASH_PATTERNS.get(stroke.dash, ())
        return tuple(part * width for part in pattern)

    def line(
        self, layer_id: str, points: Sequence[tuple[float, float]], layer: Layer
    ) -> list[Node]:
        stroke = self.stroke(layer)
        if stroke is None or stroke.color is None:
            return []
        kk = self._kk
        return [
            kk["PathNode2D"](
                id=layer_id,
                path=kk["Path2D"].polyline([self.geometry.world(p) for p in points]),
                color=self.color(stroke.color, stroke.opacity),
                width=float(stroke.width or 1.0),
                dash=self.dash(stroke),
                z=layer.z_index,
            )
        ]

    def head(
        self, layer_id: str, start: tuple[float, float], end: tuple[float, float], layer: Layer
    ) -> list[Node]:
        stroke = self.stroke(layer)
        if stroke is None or stroke.color is None:
            return []
        a, b = self.geometry.world(start), self.geometry.world(end)
        width = float(stroke.width or 1.0)
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = (dx * dx + dy * dy) ** 0.5
        if length == 0:
            return []
        ux, uy = dx / length, dy / length
        back = ARROW_HEAD_LENGTH * width
        half = ARROW_HEAD_HALF_WIDTH * width
        base = (b[0] - ux * back, b[1] - uy * back)
        corners = [
            b,
            (base[0] - uy * half, base[1] + ux * half),
            (base[0] + uy * half, base[1] - ux * half),
        ]
        kk = self._kk
        return [
            kk["Shape2D"](
                id=f"{layer_id}.head",
                path=kk["Path2D"].polygon(corners),
                fill=self.color(stroke.color, stroke.opacity),
                z=layer.z_index,
            )
        ]

    def text(
        self,
        layer_id: str,
        label: str,
        position: tuple[float, float],
        layer: Layer,
        *,
        horizontal: str,
        vertical: str,
        offset: tuple[float, float] = (0.0, 0.0),
    ) -> list[Node]:
        text_style = self.bundle(layer).text
        size = float(text_style.size) if text_style and text_style.size else DEFAULT_TEXT_SIZE
        color = self.color(text_style.color) if text_style and text_style.color else None
        asset = self.typography.asset(label, size)
        x, y = self.geometry.world(position)
        x += offset[0]
        y += offset[1]
        x -= {"left": 0.0, "center": asset.width / 2, "right": asset.width}[horizontal]
        y -= BASELINE_SHARE[vertical] * size
        kk = self._kk
        extra = {"color": color} if color is not None else {}
        return [
            kk["Text2D"](
                id=layer_id,
                asset=asset,
                position=kk["Vec2"](x, y),
                scale=1.0,
                z=layer.z_index + 10,
                **extra,
            )
        ]

    def point_label(self, layer: PointLabelLayer) -> list[Node]:
        """The label at the corner of its point that crosses the fewest lines and labels."""
        text_style = self.bundle(layer).text
        size = float(text_style.size) if text_style and text_style.size else DEFAULT_TEXT_SIZE
        asset = self.typography.asset(layer.text, size)
        width, height = asset.width, size
        px, py = self.geometry.world(layer.point)
        best = None
        for horizontal, vertical in LABEL_CORNERS:
            left = px + LABEL_GAP if horizontal == "left" else px - LABEL_GAP - width
            bottom = py + LABEL_GAP if vertical == "bottom" else py - LABEL_GAP - height
            box = (left, bottom, left + width, bottom + height)
            cost = self.crossings(box) + sum(_overlap(box, other) for other in self.placed)
            cost += 0 if self.inside(box) else 1
            if best is None or cost < best[0]:
                best = (cost, box, horizontal, vertical)
        assert best is not None
        _, box, horizontal, vertical = best
        self.placed.append(box)
        return self.text(
            layer.id,
            layer.text,
            layer.point,
            layer,
            horizontal=horizontal,
            vertical=vertical,
            offset=(
                LABEL_GAP if horizontal == "left" else -LABEL_GAP,
                LABEL_GAP if vertical == "bottom" else -LABEL_GAP,
            ),
        )

    def inside(self, box: tuple[float, float, float, float]) -> bool:
        left, bottom, right, top = self.geometry.plot
        return box[0] >= left and box[2] <= right and box[3] <= top

    def crossings(self, box: tuple[float, float, float, float]) -> int:
        return sum(_segment_hits_box(a, b, box) for a, b in self.segments)

    def __call__(self, layer: Layer) -> list[Node]:
        kk = self._kk
        if not layer.visible:
            return []
        if isinstance(layer, PathLayer):
            points = list(layer.path)
            nodes = self.line(layer.id, points, layer)
            stroke = self.stroke(layer)
            if stroke is not None and stroke.arrow is not None and len(points) >= 2:
                nodes += self.head(layer.id, points[-2], points[-1], layer)
            return nodes
        if isinstance(layer, ArrowLayer):
            return self.line(layer.id, [layer.start, layer.end], layer) + self.head(
                layer.id, layer.start, layer.end, layer
            )
        if isinstance(layer, FillLayer):
            fill = self.bundle(layer).fill
            if fill is None or fill.color is None:
                return []
            return [
                kk["Shape2D"](
                    id=layer.id,
                    path=kk["Path2D"].polygon([self.geometry.world(p) for p in layer.boundary]),
                    fill=self.color(fill.color, fill.opacity),
                    z=layer.z_index,
                )
            ]
        if isinstance(layer, MarkerLayer):
            marker = self.bundle(layer).marker
            if marker is None or marker.color is None:
                return []
            radius = float(marker.size or DEFAULT_MARKER_AREA) ** 0.5 / 2
            return [
                kk["Point2D"](
                    id=f"{layer.id}.{index}",
                    position=kk["Vec2"](*self.geometry.world(point)),
                    size=radius,
                    color=self.color(marker.color, marker.opacity),
                    z=layer.z_index,
                )
                for index, point in enumerate(layer.points)
            ]
        if isinstance(layer, TextLayer):
            return self.text(
                layer.id,
                layer.text,
                layer.position,
                layer,
                horizontal=_horizontal(layer.anchor),
                vertical=_vertical(layer.anchor),
                offset=layer.total_offset,
            )
        if isinstance(layer, PointLabelLayer):
            return self.point_label(layer)
        if isinstance(layer, AxisMarkLayer):
            spec = self.spec
            label = _plain(layer.label, layer.math)
            if layer.axis == "x":
                return self.text(
                    layer.id,
                    label,
                    (layer.value, spec.y_min),
                    layer,
                    horizontal="center",
                    vertical="top",
                    offset=(0.0, -LABEL_GAP),
                )
            return self.text(
                layer.id,
                label,
                (spec.x_min, layer.value),
                layer,
                horizontal="right",
                vertical="center",
                offset=(-LABEL_GAP, 0.0),
            )
        return []
