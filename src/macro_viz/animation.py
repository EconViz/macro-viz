"""Animate any figure builder over a parameter with KineticKit (optional dependency).

A *builder* is a function from one number (a shift, a saving rate, a round) to a MosaicKit
canvas: the very function that draws the static figure, with every range fixed by the caller so
the axes stay put. The frames are that builder's canvases at each value, so the animated and
the static figure share one geometry source and there is no second drawing code.

``save_gif`` renders every frame through MosaicKit and streams the pixels through KineticKit's
GIF exporter (``pip install macro-viz[animation]``). ``save_svg`` depicts the frames' layers as
KineticKit nodes keyed by their stable ids and lets KineticKit morph between frames into a native
animated SVG; it typesets labels with GlyphKit from the font files of the active configuration
(``[font]`` and ``[fonts]`` of ``econ-viz.toml``). Static figures never import KineticKit.
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mosaickit import (
    ArrowLayer,
    AxisMarkLayer,
    Canvas,
    CanvasGrid,
    FillLayer,
    Layer,
    MarkerLayer,
    PathLayer,
    PointLabelLayer,
    TextLayer,
)
from mosaickit.styles import DashStyle
from mosaickit.themes import StyleBundle

from macro_viz.config import active_config
from macro_viz.errors import ValidationError

if TYPE_CHECKING:  # pragma: no cover
    from kinetickit.scene.node import Node

Builder = Callable[[float], Canvas | CanvasGrid]
"""A function from a parameter value to the canvas drawing the figure at that value."""

DEFAULT_FPS = 12
DEFAULT_DPI = 150
DEFAULT_STEP_SECONDS = 0.8
"""Seconds KineticKit takes to morph from one frame to the next in an animated SVG."""

POINTS_PER_INCH = 72.0
MARGIN_POINTS = (46.0, 40.0, 34.0, 34.0)
"""Left, bottom, right, and top space around the axes in an animated SVG, in points."""

DASH_PATTERNS = {
    DashStyle.DASHED: (5.0, 3.0),
    DashStyle.DOTTED: (1.0, 3.0),
    DashStyle.DASHDOT: (5.0, 3.0, 1.0, 3.0),
}
"""Dash and gap lengths in multiples of the line width, per dash style."""

ARROW_HEAD_LENGTH = 8.0
ARROW_HEAD_HALF_WIDTH = 3.4
"""Arrowhead length and half width in multiples of the line width."""

LABEL_GAP = 5.0
"""Gap in points between a point and the label an animated SVG places beside it."""

LABEL_CORNERS = (("left", "bottom"), ("right", "bottom"), ("left", "top"), ("right", "top"))
"""Where a point label may sit relative to its point, in order of preference."""

DEFAULT_TEXT_SIZE = 11.0
"""Font size in points of a label whose theme role names none."""

DEFAULT_MARKER_AREA = 36.0
"""Area in square points of a marker whose theme role names no size."""

SEGMENT_SAMPLES = 12
"""How many points along a line are tested when a label is placed beside it."""

BASELINE_SHARE = {"top": 0.78, "center": 0.34, "bottom": 0.0}
"""Where the baseline sits below the anchor, as a share of the font size, per vertical anchor."""


def linear_values(start: float, stop: float, frames: int) -> tuple[float, ...]:
    """``frames`` evenly spaced values from ``start`` to ``stop`` inclusive."""
    if isinstance(frames, bool) or not isinstance(frames, int) or frames < 2:
        raise ValidationError("an animation needs at least two frames")
    step = (stop - start) / (frames - 1)
    return tuple(start + k * step for k in range(frames))


def frames(builder: Builder, values: Sequence[float]) -> list[Canvas | CanvasGrid]:
    """The canvas of ``builder`` at each of ``values``."""
    if not values:
        raise ValidationError("an animation needs at least one value")
    return [builder(float(value)) for value in values]


def _require_kinetickit() -> None:
    try:
        import kinetickit  # noqa: F401
    except ImportError as error:
        raise ImportError(
            "KineticKit is required to animate figures.\n"
            "Install it with:  pip install macro-viz[animation]"
        ) from error


def _png_frames(builder: Builder, values: Sequence[float], dpi: int, stem: str) -> Iterator[bytes]:
    """PNG bytes of every frame, padded with white to one common size.

    Labels that change width (a mark ``p'`` against ``p''``) make the tight bounding box differ
    from frame to frame; a GIF needs one size.
    """
    import io

    from PIL import Image

    with tempfile.TemporaryDirectory(prefix="macro-viz-animation-") as directory:
        images: list[Image.Image] = []
        for index, canvas in enumerate(frames(builder, values)):
            options: dict[str, Any] = {"transparent": False}
            if hasattr(canvas, "spec"):
                canvas.spec = canvas.spec.replace(dpi=dpi)
            else:  # a grid renders at the highest resolution of its cells
                for placement in canvas.placements:
                    placement.canvas.spec = placement.canvas.spec.replace(dpi=dpi)
            # Named after the animation, so per-figure label overrides reach every frame.
            target = Path(directory) / f"{index:06d}" / f"{stem}.png"
            target.parent.mkdir(parents=True, exist_ok=True)
            canvas.save(target, **options)
            with Image.open(target) as opened:
                images.append(opened.convert("RGB"))
        width = max(image.width for image in images)
        height = max(image.height for image in images)
        for image in images:
            padded = Image.new("RGB", (width, height), "white")
            padded.paste(image, (0, 0))
            buffer = io.BytesIO()
            padded.save(buffer, format="PNG")
            yield buffer.getvalue()


def save_gif(
    builder: Builder,
    values: Sequence[float],
    path: str | Path,
    *,
    fps: int = DEFAULT_FPS,
    dpi: int = DEFAULT_DPI,
    loop: int = 0,
) -> Path:
    """Render ``builder`` at each value through MosaicKit and write a GIF with KineticKit."""
    _require_kinetickit()
    try:
        from kinetickit.exporters import export_png_frames
    except ImportError as error:
        raise ImportError(
            "KineticKit's raster capability is required for GIF export.\n"
            "Install it with:  pip install macro-viz[animation]"
        ) from error
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    export_png_frames(
        _png_frames(builder, values, dpi, target.stem), target, fps=fps, loop=loop, disposal=2
    )
    return target


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


def _horizontal(anchor: str) -> str:
    return (
        "left"
        if anchor.endswith("left") or anchor == "left"
        else ("right" if anchor.endswith("right") or anchor == "right" else "center")
    )


def _vertical(anchor: str) -> str:
    return (
        "top" if anchor.startswith("top") else "bottom" if anchor.startswith("bottom") else "center"
    )


def _plain(label: str, math: bool) -> str:
    """Axis-mark text as a ``$...$`` formula when it is math."""
    return f"${label}$" if math else label


class _Typography:
    """GlyphKit text assets in the configured fonts, one typography per font size."""

    def __init__(self) -> None:
        from glyphkit import FontLibrary, FontSource

        settings = active_config().settings
        fonts = settings.fonts
        faces = tuple(getattr(fonts, "serif", ()) or ()) if fonts is not None else ()
        if not faces:
            raise ValidationError(
                "animated SVG needs font files: set [fonts] in econ-viz.toml "
                "(for example serif = [...]) and [font] math"
            )
        self._text = self._library(FontLibrary, FontSource, faces)
        math_font = settings.math_font
        self._math = (
            self._library(FontLibrary, FontSource, (Path(math_font.path),))
            if math_font is not None
            else None
        )
        self._cache: dict[tuple[str, float], Any] = {}

    @staticmethod
    def _library(library: Any, source: Any, paths: Sequence[Any]) -> tuple[Any, tuple[str, ...]]:
        fonts = library.from_sources(tuple(source.path(Path(path)) for path in paths))
        return fonts, tuple(dict.fromkeys(face.family for face in fonts.faces))

    def _typography(self, kind: str, size: float) -> Any:
        from kinetickit.integrations.glyphkit import GlyphKitTypography

        key = (kind, size)
        if key not in self._cache:
            library, families = self._math if kind == "math" and self._math else self._text
            self._cache[key] = GlyphKitTypography(library, families=families, size=size)
        return self._cache[key]

    def asset(self, label: str, size: float) -> Any:
        is_math = len(label) > 2 and label.startswith("$") and label.endswith("$")
        if is_math and self._math is not None:
            return self._typography("math", size).math(label[1:-1])
        return self._typography("text", size).asset(label.strip("$") if is_math else label)


def save_svg(
    builder: Builder,
    values: Sequence[float],
    path: str | Path,
    *,
    step_seconds: float = DEFAULT_STEP_SECONDS,
    margin: tuple[float, float, float, float] = MARGIN_POINTS,
) -> Path:
    """Morph between ``builder``'s frames into a native animated SVG with KineticKit."""
    _require_kinetickit()
    if len(values) < 2:
        raise ValidationError("an animated SVG needs at least two frames")
    from kinetickit.adapters import transition
    from kinetickit.animation import Animation
    from kinetickit.geometry.two_d import Bounds2D, Vec2

    canvases = [canvas for canvas in frames(builder, values) if isinstance(canvas, Canvas)]
    if len(canvases) != len(values):
        raise ValidationError("an animated SVG needs single canvases; use save_gif for panels")
    geometry = _geometry(canvases[0], margin)
    typography = _Typography()
    layer_sets = [list(canvas.snapshot().layers) for canvas in canvases]
    per_frame = [_Depicter(canvas, geometry, typography) for canvas in canvases]
    depicters = {
        id(layer): depicter
        for depicter, layers in zip(per_frame, layer_sets, strict=True)
        for layer in layers
    }

    def depict(layer: Layer) -> list[Node]:
        return depicters[id(layer)](layer)

    steps = [
        transition(before, after, depict, duration=step_seconds)
        for before, after in zip(layer_sets, layer_sets[1:], strict=False)
    ]
    motion = steps[0].motion
    for step in steps[1:]:
        motion = motion.then(step.motion)
    scene = steps[0].scene
    view = Bounds2D(Vec2(0.0, 0.0), Vec2(geometry.width, geometry.height))
    scene = scene.bind({scene.camera.ref("view"): view})
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    Animation(scene, motion).save(
        target, renderer="vector", width=geometry.width, height=geometry.height
    )
    return target


__all__ = [
    "DEFAULT_DPI",
    "DEFAULT_FPS",
    "DEFAULT_STEP_SECONDS",
    "Builder",
    "frames",
    "linear_values",
    "save_gif",
    "save_svg",
]
