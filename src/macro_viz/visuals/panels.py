"""Linked-panel diagrams: several panels on one mosaickit grid, joined by dashed projections.

Every panel is an ordinary canvas whose axes show a solved variable over the same length as
every other panel that shows that variable, so a value read in one panel lands on the same pixel
column (or row) in the next. The dashed paths are ``GridLink`` objects drawn from data
coordinates, never from positions typed in. Curves, points, ticks and arrows come from
``macro_viz.panels`` and are drawn with the ``macro.*`` theme roles; all text is looked up in
the locale table.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from bezierkit import Point as BezierPoint
from bezierkit.construction import RotationConnector
from mosaickit import (
    ArrowPlacement,
    ArrowStyle,
    Canvas,
    CanvasGrid,
    Layer,
    MarkerLayer,
    PathLayer,
    Span,
    Stroke,
    TextLayer,
)
from mosaickit.canvas.grid_link import GridLink
from mosaickit.layout import Rect, place_rotation_marker

from macro_viz.config import active_config
from macro_viz.errors import ValidationError
from macro_viz.i18n import Labels
from macro_viz.panels import (
    ArrowOptions,
    CurveOptions,
    Hop,
    Mode,
    PanelLayout,
    PanelSpec,
    PanelState,
    Scenario,
    axis_lengths,
    curve_specs,
    five_panel_layout,
    four_panel_layout,
    shift_arrows,
)
from macro_viz.panels.arrows import ShiftArrow
from macro_viz.panels.curves import (
    DEFAULT_SAMPLES,
    KEY_DIGITS,
    CurveSpec,
    Ranges,
    Subscripted,
    clip,
)
from macro_viz.panels.layout import DIAGONAL, X_AXIS
from macro_viz.panels.model import N, P, R, W, Y
from macro_viz.panels.movement import MovementKind
from macro_viz.visuals._kit import axes_layers, canvas_spec, new_canvas
from macro_viz.visuals._placement import (
    CURVE_ORDER,
    POINT_ORDER,
    Box,
    Placed,
    PlacementOptions,
    Scene,
    is_free,
    place,
    text_box,
)

COLUMN_GAP = 0.12
"""Default gap between grid columns, as a share of a column's width."""

OUTER_MARGIN = 0.01
"""Default margin around the whole figure, as a share of its size."""

ROW_GAP = 0.0
"""Default gap between grid rows, as a share of a row's height (tick labels sit inside panels)."""

PANEL_WIDTH = 4.3
"""Width in inches of one grid column."""

DEFAULT_EXTENT = 1.7
"""Axis length as a multiple of the largest solved value shown on it."""

DEFAULT_PAD = {N: 0.3, Y: 0.3, W: 0.1, P: 0.1, R: 0.1}
"""Room right of each variable's horizontal axis for curve names, as a share of its length."""

TOP_PAD = 0.08
"""Room above a vertical axis for its arrowhead and title, as a share of its length."""

MARGIN = 0.14
"""Room under and left of each axis for tick labels, as a share of the axis length."""

TICK_CLEARANCE = 0.1
"""Tick labels closer than this share of the panel's range lean away from each other."""

LABEL_GAP = 0.13
"""How much of a panel's height a dashed path stops short of a tick label under an axis."""

UPPER_RIGHT_TAIL_LABELS = frozenset(("lm", "sras"))
"""Curve families whose names stay directly above-right of their upper-right endpoint."""

SYMBOL_IDS = {
    N: "panels.var.employment",
    W: "panels.var.wage",
    Y: "panels.var.output",
    P: "panels.var.price",
    R: "panels.var.rate",
}
"""The locale id of each variable's symbol."""

POINTS_PER_INCH = 72.0

TICK_OFFSET = 4.0
"""Distance in points between an axis and its tick label."""

DIAGONAL_REACH = 0.97
"""The share of the axis the 45-degree line runs before its arrowhead."""

ARROW = Stroke(arrow=ArrowStyle.TRIANGLE)

ROTATION_SAMPLES = 48
"""Sampling resolution for a Bézier marker; placement and curvature do not depend on it."""


def _normalise_path(
    points: Sequence[tuple[float, float]], extent: tuple[float, float]
) -> tuple[tuple[float, float], ...]:
    return tuple((x / extent[0], y / extent[1]) for x, y in points)


def _line_intersection(
    first: CurveSpec, second: CurveSpec, extent: tuple[float, float]
) -> tuple[float, float]:
    """Intersection of two curve endpoint chords in normalised panel coordinates."""
    a, b = _normalise_path((first.points[0], first.points[-1]), extent)
    c, d = _normalise_path((second.points[0], second.points[-1]), extent)
    ab = (b[0] - a[0], b[1] - a[1])
    cd = (d[0] - c[0], d[1] - c[1])
    denominator = ab[0] * cd[1] - ab[1] * cd[0]
    if abs(denominator) < 1e-12:
        raise ValidationError("rotation curves must have a common finite pivot")
    offset = (c[0] - a[0], c[1] - a[1])
    share = (offset[0] * cd[1] - offset[1] * cd[0]) / denominator
    return a[0] + share * ab[0], a[1] + share * ab[1]


def _rotation_connector(
    start: tuple[float, float], end: tuple[float, float], pivot: tuple[float, float]
) -> tuple[tuple[float, float], ...]:
    curve = RotationConnector(BezierPoint(*start), BezierPoint(*end), BezierPoint(*pivot)).build()
    parameters = [index / (ROTATION_SAMPLES - 1) for index in range(ROTATION_SAMPLES)]
    return tuple(tuple(point.coords) for point in curve.at_many(parameters))  # type: ignore[misc]


def _rotation_arrows(
    panel: PanelSpec,
    curves: Sequence[CurveSpec],
    lengths: Mapping[str, float],
    kinds: Mapping[str, MovementKind],
    options: ArrowOptions,
) -> list[ShiftArrow]:
    """Place typed rotation markers in the visual layer using display-neutral geometry."""
    extent = lengths[panel.x], lengths[panel.y]
    families: dict[str, list[CurveSpec]] = defaultdict(list)
    for curve in curves:
        if kinds.get(curve.family) is MovementKind.ROTATION:
            families[curve.family].append(curve)

    arrows = []
    for family, members in families.items():
        accepted: list[tuple[tuple[float, float], ...]] = []
        for old, new in zip(members, members[1:], strict=False):
            old_path = _normalise_path(old.points, extent)
            new_path = _normalise_path(new.points, extent)
            if family == "production":
                pivot = (0.0, 0.0)
                old_path = (pivot, *old_path)
                new_path = (pivot, *new_path)
            else:
                pivot = _line_intersection(old, new, extent)
            placement = place_rotation_marker(
                old_path,
                new_path,
                pivot,
                Rect(0.0, 0.0, 1.0, 1.0),
                _rotation_connector,
                accepted=accepted,
                clearance=options.rotation_clearance,
                search_step=options.rotation_search_step,
                minimum_span=options.rotation_clearance,
            )
            if placement is None:
                raise ValidationError(f"could not place a rotation marker for {family}")
            accepted.append(placement.path)
            points = tuple((x * extent[0], y * extent[1]) for x, y in placement.path)
            arrows.append(ShiftArrow(panel.key, family, points))
    return arrows


def _shifted_states(
    states: Sequence[PanelState], origins: Mapping[str, float]
) -> tuple[PanelState, ...]:
    """The states with every value measured from its axis origin."""
    return tuple(
        replace(
            state,
            values={name: value - origins.get(name, 0.0) for name, value in state.values.items()},
        )
        for state in states
    )


@dataclass(frozen=True, slots=True)
class _Window:
    """Curves are built from the model's own values, then moved into the shown window."""

    origins: Mapping[str, float]
    lengths: Mapping[str, float]
    headroom: float

    def _absolute(self, variable: str) -> float:
        """Axis length that keeps the model-value clip at the top of the shown window."""
        return self.origins.get(variable, 0.0) / self.headroom + self.lengths[variable]

    def ranges(self) -> Ranges:
        return Ranges({name: self._absolute(name) for name in self.lengths})

    def options(
        self,
        base: CurveOptions,
        states: Sequence[PanelState],
        tails: Mapping[str, float],
        demand_tail: float | None,
    ) -> CurveOptions:
        n = [state.values[N] for state in states]
        n_length, y_length = self._absolute(N), self._absolute(Y)
        tail_n = tails.get(N, 0.0)
        return replace(
            base,
            span=((min(n) - tail_n) / n_length, (max(n) + tail_n) / n_length),
            demand_start=(min(n) - (tail_n if demand_tail is None else demand_tail)) / n_length,
            reach=tails.get(Y, base.reach * y_length) / y_length,
        )

    def shift(self, curves: Sequence[CurveSpec], panel: PanelSpec) -> list[CurveSpec]:
        if not self.origins:
            return list(curves)
        dx, dy = self.origins.get(panel.x, 0.0), self.origins.get(panel.y, 0.0)
        box_x, box_y = self.headroom * self.lengths[panel.x], self.headroom * self.lengths[panel.y]
        shifted = []
        for curve in curves:
            moved = [(x - dx, y - dy) for x, y in curve.points]
            shifted.append(replace(curve, points=clip(moved, box_x, box_y)))
        return shifted


@dataclass(frozen=True, slots=True)
class _Context:
    layout: PanelLayout
    states: Sequence[PanelState]
    lengths: Mapping[str, float]
    pad: Mapping[str, float]
    labels: Labels
    margin: float
    top_pad: float

    def symbol(self, variable: str) -> str:
        return self.labels(SYMBOL_IDS[variable])

    def subscripted(self, value: Subscripted | int) -> str:
        if isinstance(value, int):
            return str(value)
        text = self.labels(f"panels.var.{value.symbol}")
        return text if value.index is None else f"{text}_{value.index}"

    def _range(self, variable: str, pad: float) -> tuple[float, float]:
        length = self.lengths[variable]
        return (-self.margin * length, length * (1 + pad))

    def x_range(self, panel: PanelSpec) -> tuple[float, float]:
        return self._range(panel.x, self.pad[panel.x])

    def y_range(self, panel: PanelSpec) -> tuple[float, float]:
        return self._range(panel.y, self.top_pad)


def _present(state: PanelState, panel: PanelSpec) -> bool:
    return panel.x in state.values and panel.y in state.values


def _aspect(ctx: _Context, layout: PanelLayout) -> float:
    """Height over width of the 45-degree panel's data range (1 without such a panel)."""
    reference = next((p for p in layout.panels if p.kind == DIAGONAL), None)
    if reference is None:
        return 1.0
    (x0, x1), (y0, y1) = ctx.x_range(reference), ctx.y_range(reference)
    return (y1 - y0) / (x1 - x0)


def _unit_height(
    layout: PanelLayout,
    width: float,
    column_gap: float,
    row_gap: float,
    outer: float,
    aspect: float,
) -> float:
    """Height of one grid row that gives the 45-degree line exactly 45 degrees.

    ``aspect`` is the height of that panel's data range over its width.
    """
    reference = next((p for p in layout.panels if p.kind == DIAGONAL), None)
    if reference is None:
        return width

    def extent(units: int, gap: float) -> float:
        return units + gap * (units - 1)

    cols, rows = layout.cols, layout.rows
    inner = 1 - 2 * outer
    cell_width = width * cols * inner / extent(cols, column_gap)
    panel_width = cell_width * extent(reference.cols, column_gap)
    cell_height = aspect * panel_width / extent(reference.rows, row_gap)
    return cell_height * extent(rows, row_gap) / inner / rows


def _panel_renderer() -> Any:
    """The matplotlib renderer with the row, column and outer gaps of a ``PanelGrid``.

    Imported here because the renderer module needs the text engine, which static
    figures built without it must not require until they are saved.
    """
    from mosaickit.rendering.matplotlib.renderer import MatplotlibRenderer

    class PanelRenderer(MatplotlibRenderer):
        def render_grid(self, grid: Any, cache: Any) -> Any:
            result = super().render_grid(grid, cache)
            result.figure.subplots_adjust(
                left=grid.outer,
                right=1 - grid.outer,
                bottom=grid.outer,
                top=1 - grid.outer,
                wspace=grid.column_gap,
                hspace=grid.row_gap,
            )
            return result

    return PanelRenderer()


class PanelGrid(CanvasGrid):
    """A ``CanvasGrid`` drawn with its own gaps between rows and columns (shares of a cell)."""

    def __init__(
        self, *args: Any, column_gap: float, row_gap: float, outer: float, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.column_gap, self.row_gap, self.outer = column_gap, row_gap, outer

    def _renderer(self, renderer: Any = None) -> Any:
        return _panel_renderer() if renderer is None else super()._renderer(renderer)


def _text_layer(
    position: tuple[float, float], text: str, axis: str, layer_id: str, lean: str = "center"
) -> TextLayer:
    """A tick label; ``lean`` ``left`` or ``right`` ends or starts the label at its tick."""
    if axis == X_AXIS:
        anchor = {"center": "top", "left": "top-right", "right": "top-left"}[lean]
        return TextLayer(
            position,
            text,
            id=layer_id,
            role="macro.mark",
            anchor=anchor,
            offset=(0, -TICK_OFFSET),
            math=True,
        )
    anchor = {"center": "right", "left": "top-right", "right": "bottom-right"}[lean]
    return TextLayer(
        position,
        text,
        id=layer_id,
        role="macro.mark",
        anchor=anchor,
        offset=(-TICK_OFFSET, 0),
        math=True,
    )


def _leans(values: Sequence[float], span: float) -> list[str]:
    """For tick positions along one axis: ``left`` for a label that leans left (the left one of
    two crowded ticks), ``right`` for the right one, ``center`` otherwise."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    lean = ["center"] * len(values)
    for first, second in zip(order, order[1:], strict=False):
        if values[second] - values[first] < TICK_CLEARANCE * span:
            if lean[first] == "center":
                lean[first] = "left"
            if lean[second] == "center":
                lean[second] = "right"
    return lean


def _ticks(
    ctx: _Context, hidden: Collection[tuple[str, str]]
) -> tuple[dict[str, list[Layer]], set[tuple[str, str, str, float]]]:
    """The tick labels of every panel, and which (panel, axis, variable, value) were drawn."""
    found: dict[tuple[str, str], list[tuple[float, str, str]]] = {}
    drawn: set[tuple[str, str, str, float]] = set()
    seen: set[tuple[str, float]] = set()
    for tick in ctx.layout.ticks:
        panel = ctx.layout.panel(tick.panel)
        for state in ctx.states:
            value = state.values.get(tick.variable)
            if value is None or not _present(state, panel):
                continue
            if (tick.variable, state.label) in hidden:
                continue
            marker = (tick.variable, round(value, KEY_DIGITS))
            if marker in seen:
                continue
            seen.add(marker)
            drawn.add((tick.panel, tick.axis, tick.variable, marker[1]))
            name = f"${ctx.symbol(tick.variable)}_{state.subscript(tick.variable)}$"
            layer_id = f"macro.panels.{tick.panel}.tick.{tick.variable}.{state.label}"
            found.setdefault((tick.panel, tick.axis), []).append((value, name, layer_id))
    layers: dict[str, list[Layer]] = {panel.key: [] for panel in ctx.layout.panels}
    for (name_of_panel, axis), items in found.items():
        panel = ctx.layout.panel(name_of_panel)
        low, high = ctx.x_range(panel) if axis == X_AXIS else ctx.y_range(panel)
        leans = _leans([value for value, _, _ in items], high - low)
        for (value, name, layer_id), lean in zip(items, leans, strict=True):
            position = (value, 0.0) if axis == X_AXIS else (0.0, value)
            layers[name_of_panel].append(_text_layer(position, name, axis, layer_id, lean))
    return layers, drawn


@dataclass(frozen=True, slots=True)
class _Segment:
    """One dashed stretch between two points, each in its own panel's data coordinates."""

    first: str
    start: tuple[float, float]
    second: str
    end: tuple[float, float]


def _segments(
    ctx: _Context,
    projections: Collection[str] | None,
    steps: Collection[str],
    drawn: set[tuple[str, str, str, float]],
    gap: float,
) -> list[_Segment]:
    segments: list[_Segment] = []

    def point(hop: Hop, state: PanelState) -> tuple[float, float] | None:
        x = 0.0 if hop.x is None else state.values.get(hop.x)
        y = 0.0 if hop.y is None else state.values.get(hop.y)
        return None if x is None or y is None else (x, y)

    def below(hop: Hop, other: Hop) -> bool:
        if hop.panel == other.panel:
            return False
        return ctx.layout.panel(other.panel).row > ctx.layout.panel(hop.panel).row

    for state in ctx.states:
        if state.label not in steps:
            continue
        for projection in ctx.layout.projections:
            if projections is not None and projection.name not in projections:
                continue
            for path in projection.paths:
                points = [point(hop, state) for hop in path]
                if any(p is None for p in points):
                    continue
                for index, (first, second) in enumerate(zip(path, path[1:], strict=False)):
                    start, end = points[index], points[index + 1]
                    assert start is not None and end is not None
                    start = _cleared(ctx, first, second, start, state, drawn, gap, below)
                    end = _cleared(ctx, second, first, end, state, drawn, gap, below)
                    if first.panel == second.panel and start == end:
                        continue
                    segments.append(_Segment(first.panel, start, second.panel, end))
    return segments


def _split(
    ctx: _Context, segment: _Segment
) -> tuple[
    tuple[str, tuple[float, float], tuple[float, float]] | None,
    tuple[str, tuple[float, float], str, tuple[float, float]] | None,
    tuple[str, tuple[float, float], tuple[float, float]] | None,
]:
    """A segment as (piece in the first panel, crossing of the gap, piece in the second).

    Within one panel the whole segment is the first piece. Between panels each piece runs to the
    panel's edge and the crossing is a ``GridLink`` from edge to edge, so the dashed path is one
    line whose ends lie exactly on the data points.
    """
    if segment.first == segment.second:
        return (segment.first, segment.start, segment.end), None, None
    a, b = ctx.layout.panel(segment.first), ctx.layout.panel(segment.second)
    (x0, y0), (x1, y1) = segment.start, segment.end
    if (a.col, a.cols) == (b.col, b.cols) and x0 == x1:
        down = b.row > a.row
        a_edge = ctx.y_range(a)[0 if down else 1]
        b_edge = ctx.y_range(b)[1 if down else 0]
        exit_, entry = (x0, a_edge), (x1, b_edge)
    else:
        right = b.col > a.col
        a_edge = ctx.x_range(a)[1 if right else 0]
        b_edge = ctx.x_range(b)[0 if right else 1]
        exit_, entry = (a_edge, y0), (b_edge, y1)
    return (
        (a.key, segment.start, exit_),
        (a.key, exit_, b.key, entry),
        (b.key, entry, segment.end),
    )


def _cleared(
    ctx: _Context,
    hop: Hop,
    other: Hop,
    point: tuple[float, float],
    state: PanelState,
    drawn: set[tuple[str, str, str, float]],
    gap: float,
    below: Callable[[Hop, Hop], bool],
) -> tuple[float, float]:
    """``point``, moved off the axis when a tick label sits there and the path leaves below."""
    if not hop.cleared or hop.x is None:
        return point
    value = state.values[hop.x]
    if (hop.panel, X_AXIS, hop.x, round(value, KEY_DIGITS)) not in drawn:
        return point
    if not below(hop, other):
        return point
    panel = ctx.layout.panel(hop.panel)
    return (point[0], -gap * ctx.lengths[panel.y])


def _tick_box(
    layer: Layer,
    scale: tuple[float, float],
    origin: tuple[float, float],
    size: float,
    o: PlacementOptions,
) -> Box:
    """The estimated box in points of a tick label (a ``TextLayer`` of ``_text_layer``)."""
    assert isinstance(layer, TextLayer)
    w, h = text_box(str(layer.text), size, o)
    x = (layer.position[0] - origin[0]) * scale[0] + layer.offset[0]
    y = (layer.position[1] - origin[1]) * scale[1] + layer.offset[1]
    horizontal, _, vertical = layer.anchor.partition("-")[::-1] if False else (None, None, None)
    del horizontal, vertical
    names = layer.anchor
    left = "left" in names
    right = "right" in names
    top = "top" in names
    bottom = "bottom" in names
    x0 = x if left else x - w if right else x - w / 2
    y0 = y - h if top else y if bottom else y - h / 2
    return (x0, y0, x0 + w, y0 + h)


def _axes_size_pt(
    layout: PanelLayout,
    panel: PanelSpec,
    width: float,
    height: float,
    column_gap: float,
    row_gap: float,
    outer: float,
) -> tuple[float, float]:
    """Width and height in points of the axes of ``panel`` once the grid is drawn."""
    inner = 1 - 2 * outer

    def extent(units: int, gap: float) -> float:
        return units + gap * (units - 1)

    w = (
        width
        * layout.cols
        * inner
        * extent(panel.cols, column_gap)
        / extent(layout.cols, column_gap)
    )
    h = height * layout.rows * inner * extent(panel.rows, row_gap) / extent(layout.rows, row_gap)
    return (w * POINTS_PER_INCH, h * POINTS_PER_INCH)


def _upper_right_of_tail(
    anchor: tuple[float, float],
    size: tuple[float, float],
    scene: Scene,
    options: PlacementOptions,
) -> Placed:
    """Place a curve name above-right of its tail, moving farther right until unobstructed."""
    base = options.gap * 0.75
    unbounded = Scene(
        segments=scene.segments,
        boxes=scene.boxes,
        dots=scene.dots,
        limits=(-float("inf"), -float("inf"), float("inf"), float("inf")),
        dot_radius=scene.dot_radius,
    )
    for ring in range(32):
        x_gap = base + ring * options.step
        y_gap = base + ring * options.step * 0.25
        position = (anchor[0] + x_gap, anchor[1] + y_gap)
        box = (position[0], position[1], position[0] + size[0], position[1] + size[1])
        candidate = Placed(box, "bottom-left", position, None)
        if is_free(box, unbounded, options, ignore=(anchor,)):
            return candidate
    raise ValidationError("could not place a curve label above-right of its tail")


def _panel_canvas(
    ctx: _Context,
    panel: PanelSpec,
    curves: Sequence[CurveSpec],
    arrows: Sequence[ShiftArrow],
    ticks: Sequence[Layer],
    pieces: Sequence[tuple[tuple[float, float], tuple[float, float]]],
    title: str | None,
    steps: Collection[str],
    width: float,
    height: float,
    size_pt: tuple[float, float],
    placement: PlacementOptions,
) -> Canvas:
    x_range, y_range = ctx.x_range(panel), ctx.y_range(panel)
    spec = canvas_spec(
        x_range, y_range, width=panel.cols * width, height=panel.rows * height, title=title
    )
    canvas = new_canvas(spec)
    lx, ly = ctx.lengths[panel.x], ctx.lengths[panel.y]
    canvas.extend(
        axes_layers(
            (0.0, lx),
            (0.0, ly),
            x_label=f"${ctx.symbol(panel.x)}$",
            y_label=f"${ctx.symbol(panel.y)}$",
            origin_label=ctx.labels("axis.origin"),
        )
    )
    options = active_config().settings.options
    text_size = options.label_size * options.text_scale
    small_size = options.annotation_size * options.text_scale
    scale = (size_pt[0] / (x_range[1] - x_range[0]), size_pt[1] / (y_range[1] - y_range[0]))
    origin = (x_range[0], y_range[0])

    def pt(point: tuple[float, float]) -> tuple[float, float]:
        return ((point[0] - origin[0]) * scale[0], (point[1] - origin[1]) * scale[1])

    scene = Scene(limits=(0.0, 0.0, size_pt[0], size_pt[1]), dot_radius=options.point_size**0.5)
    scene.add_polyline([pt((0.0, 0.0)), pt((lx, 0.0))])
    scene.add_polyline([pt((0.0, 0.0)), pt((0.0, ly))])
    for corner, anchor_box in (
        (pt((lx, 0.0)), "x"),
        (pt((0.0, ly)), "y"),
    ):
        w, h = text_box("W", text_size, placement)
        if anchor_box == "x":
            scene.boxes.append((corner[0], corner[1] - h / 2, corner[0] + 2 * w, corner[1] + h / 2))
        else:
            scene.boxes.append((corner[0] - w, corner[1], corner[0] + w, corner[1] + 2 * h))
    if panel.kind == DIAGONAL:
        tip = DIAGONAL_REACH * min(lx, ly)
        canvas.add(
            PathLayer(
                ((0.0, 0.0), (tip, tip)),
                id=f"macro.panels.{panel.key}.diagonal",
                role="macro.diagonal",
                stroke=ARROW,
                arrow_placement=ArrowPlacement.END,
                clip=False,
            )
        )
        canvas.add(
            TextLayer(
                (tip, tip),
                ctx.labels("panels.label.diagonal"),
                id=f"macro.panels.{panel.key}.diagonal.label",
                role="macro.annotation",
                anchor="bottom-left",
                offset=(3, 2),
            )
        )
        scene.add_polyline([pt((0.0, 0.0)), pt((tip, tip))])
        w, h = text_box("45", small_size, placement)
        top = pt((tip, tip))
        scene.boxes.append((top[0], top[1], top[0] + w + 6, top[1] + h + 2))
    for piece in pieces:
        scene.add_polyline([pt(piece[0]), pt(piece[1])])
    for arrow in arrows:
        scene.add_polyline([pt(point) for point in arrow.points])
    for tick in ticks:
        scene.boxes.append(_tick_box(tick, scale, origin, small_size, placement))
    for curve in curves:
        scene.add_polyline([pt(point) for point in curve.points])
    dots: list[tuple[str, tuple[float, float]]] = []
    if panel.points:
        seen: set[tuple[float, float]] = set()
        for state in ctx.states:
            if state.label not in steps or not _present(state, panel):
                continue
            location = (state.values[panel.x], state.values[panel.y])
            key = (round(location[0], KEY_DIGITS), round(location[1], KEY_DIGITS))
            if key in seen:
                continue
            seen.add(key)
            dots.append((state.label, location))
            scene.dots.append(pt(location))

    def put(
        layer_id: str, role: str, text: str, placed: Placed, size: float, *, at_leader: bool = True
    ) -> None:
        scene.boxes.append(placed.box)
        position = (
            placed.position[0] / scale[0] + origin[0],
            placed.position[1] / scale[1] + origin[1],
        )
        canvas.add(
            TextLayer(
                position, text, id=layer_id, role=role, anchor=placed.anchor, math=True, z_index=7
            )
        )
        if placed.leader is not None and at_leader:
            start, end = placed.leader
            canvas.add(
                PathLayer(
                    tuple(
                        (v[0] / scale[0] + origin[0], v[1] / scale[1] + origin[1])
                        for v in (start, end)
                    ),
                    id=f"{layer_id}.leader",
                    role="macro.link.leader",
                    clip=False,
                    z_index=6,
                )
            )

    counts: dict[str, int] = {}
    for curve in curves:
        number = counts.get(curve.family, 0)
        counts[curve.family] = number + 1
        base = f"macro.panels.{panel.key}.{curve.family}.{number}"
        role = "macro.curve.panel" if curve.main else "macro.curve.panel.shifted"
        canvas.add(PathLayer(curve.points, id=base, role=role, z_index=2))
    for curve in curves:
        number = [c for c in curves if c.family == curve.family].index(curve)
        base = f"macro.panels.{panel.key}.{curve.family}.{number}"
        role = "macro.curve.panel" if curve.main else "macro.curve.panel.shifted"
        fields = {name: ctx.subscripted(value) for name, value in curve.fields.items()}
        label = ctx.labels(curve.label_id, **fields)
        size = text_box(label, text_size, placement)
        if "\\frac" in label:
            size = (size[0] * 1.3, size[1] * 3.0)
        anchor = pt(curve.end)
        if curve.family in UPPER_RIGHT_TAIL_LABELS:
            placed = _upper_right_of_tail(anchor, size, scene, placement)
        else:
            placed = place(anchor, size, scene, placement, CURVE_ORDER)
        put(f"{base}.label", role, label, placed, text_size)
    for number, arrow in enumerate(arrows):
        canvas.add(
            PathLayer(
                arrow.points,
                id=f"macro.panels.{panel.key}.shift.{number}",
                role="macro.shift",
                stroke=ARROW,
                arrow_placement=ArrowPlacement.END,
                z_index=5,
            )
        )
    for number, (start, end) in enumerate(pieces):
        canvas.add(
            PathLayer(
                (start, end),
                id=f"macro.panels.{panel.key}.link.{number}",
                role="macro.link",
                clip=False,
                z_index=1,
            )
        )
    canvas.extend(ticks)
    for label, location in dots:
        layer_id = f"macro.panels.{panel.key}.point.{label}"
        canvas.add(MarkerLayer((location,), id=layer_id, role="macro.point", z_index=6))
        size = text_box(label, text_size, placement)
        placed = place(pt(location), size, scene, placement, POINT_ORDER, ignore=(pt(location),))
        put(f"{layer_id}.label", "macro.point", f"${label}$", placed, text_size)
    return canvas


def linked_panels_canvas(
    scenario: Scenario,
    layout: PanelLayout,
    *,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    mode: Mode = Mode.SCHEMATIC,
    sras: bool = True,
    lras: bool = False,
    ad: bool = True,
    shifted_sras: bool = True,
    steps: Collection[str] | None = None,
    projections: Collection[str] | None = None,
    hide_ticks: Collection[tuple[str, str]] = (),
    shift_arrows_on: bool | ArrowOptions = True,
    extent: float = DEFAULT_EXTENT,
    ranges: Mapping[str, float] | None = None,
    origins: Mapping[str, float] | None = None,
    tails: Mapping[str, float] | None = None,
    demand_tail: float | None = None,
    pad: Mapping[str, float] | None = None,
    margin: float = MARGIN,
    top_pad: float = TOP_PAD,
    samples: int = DEFAULT_SAMPLES,
    label_gap: float = LABEL_GAP,
    column_gap: float = COLUMN_GAP,
    row_gap: float = ROW_GAP,
    outer: float = OUTER_MARGIN,
    placement: PlacementOptions | None = None,
    width: float = PANEL_WIDTH,
) -> CanvasGrid:
    """Draw ``scenario`` on ``layout``: curves, points, ticks, shift arrows and projections.

    ``mode`` draws curves from the equations (``DERIVED``) or as lines through the solved
    points (``SCHEMATIC``). ``sras``, ``lras`` and ``ad`` choose the curves of the AD-AS panel
    (``shifted_sras`` False keeps only the first step's SRAS).

    ``steps`` limits which steps are marked and projected (default all); ``projections``
    limits which projections are drawn, by name; ``hide_ticks`` is a collection of
    ``(variable, step label)`` pairs whose tick label is left out; ``ranges`` fixes the axis
    length of a variable.

    ``origins`` moves the corner of the axes of a variable to that solved value (the axes then
    show a window of the model rather than starting at zero) and ``ranges`` is the length of
    the window. ``tails`` keeps curves of ``N`` and ``Y`` only that far (in model units) beyond
    the outermost solved value, and ``demand_tail`` does so for the left end of labour demand.

    ``pad`` is the room right of each horizontal axis for curve names and ``top_pad`` the room
    above each vertical axis (shares of the axis length); ``margin`` the room under and left of
    the axes for tick labels; ``label_gap`` how far dashed paths stop short of a tick label;
    ``column_gap`` and ``row_gap`` the space between grid columns and rows (shares of a cell);
    ``outer`` the margin around the figure (a share of its size); ``placement`` the distances
    and text-size estimate used to place labels.

    ``title`` is drawn above the top-left panel;
    ``None`` draws none.
    """
    text = Labels(labels)
    states = scenario.solve()
    shown = {state.label for state in states} if steps is None else set(steps)
    unknown = sorted(shown - {state.label for state in states})
    if unknown:
        raise ValidationError(f"unknown steps: {unknown}")
    lengths = axis_lengths(states, extent=extent, overrides=ranges, natural=lras)
    corner = dict(origins or {})
    solved = states
    states = _shifted_states(states, corner)
    full_pad = {**DEFAULT_PAD, **(pad or {})}
    ctx = _Context(layout, states, lengths.lengths, full_pad, text, margin, top_pad)
    options = CurveOptions(
        mode=mode, samples=samples, sras=sras, shifted_sras=shifted_sras, lras=lras, ad=ad
    )
    window = _Window(corner, lengths.lengths, options.headroom)
    if corner:
        options = window.options(options, solved, tails or {}, demand_tail)
    arrow_options = shift_arrows_on if isinstance(shift_arrows_on, ArrowOptions) else ArrowOptions()
    movement_kinds = scenario.movement_kinds()
    ticks, drawn = _ticks(ctx, hide_ticks)
    height = _unit_height(layout, width, column_gap, row_gap, outer, _aspect(ctx, layout))
    placed = sorted(layout.panels, key=lambda panel: (panel.row, panel.col))
    pieces: dict[str, list[tuple[tuple[float, float], tuple[float, float]]]] = {
        panel.key: [] for panel in layout.panels
    }
    crossings: list[tuple[str, tuple[float, float], str, tuple[float, float]]] = []
    for segment in _segments(ctx, projections, shown, drawn, label_gap):
        before, crossing, after = _split(ctx, segment)
        for piece in (before, after):
            if piece is not None and piece[1] != piece[2]:
                pieces[piece[0]].append((piece[1], piece[2]))
        if crossing is not None:
            crossings.append(crossing)
    canvases: dict[str, Canvas] = {}
    for index, panel in enumerate(placed):
        curves = window.shift(curve_specs(panel, scenario, solved, window.ranges(), options), panel)
        arrows = (
            shift_arrows(
                panel,
                curves,
                states,
                dict(lengths.lengths),
                arrow_options,
                movement_kinds,
            )
            if shift_arrows_on is not False
            else []
        )
        if shift_arrows_on is not False:
            arrows += _rotation_arrows(
                panel, curves, lengths.lengths, movement_kinds, arrow_options
            )
        canvases[panel.key] = _panel_canvas(
            ctx,
            panel,
            curves,
            arrows,
            ticks[panel.key],
            pieces[panel.key],
            title if index == 0 else None,
            shown,
            width,
            height,
            _axes_size_pt(layout, panel, width, height, column_gap, row_gap, outer),
            placement or PlacementOptions(),
        )
    matrix: list[list[Span | None]] = [[None] * layout.cols for _ in range(layout.rows)]
    occupied: set[tuple[int, int]] = set()
    for panel in placed:
        matrix[panel.row][panel.col] = Span(canvases[panel.key], rows=panel.rows, cols=panel.cols)
        for r in range(panel.row, panel.row + panel.rows):
            for c in range(panel.col, panel.col + panel.cols):
                occupied.add((r, c))
    rows = []
    for r, row in enumerate(matrix):
        cells = [cell for c, cell in enumerate(row) if cell is not None or (r, c) not in occupied]
        rows.append(cells)
    cell = {panel.key: index for index, panel in enumerate(placed)}
    links = [
        GridLink(cell[first], start, cell[second], end, role="macro.link")
        for first, start, second, end in crossings
    ]
    return PanelGrid(
        rows,
        rows=layout.rows,
        cols=layout.cols,
        links=links,
        column_gap=column_gap,
        row_gap=row_gap,
        outer=outer,
    )


def four_panel_canvas(scenario: Scenario, **options: object) -> CanvasGrid:
    """Labour market, AD-AS, production function and 45-degree line (see ``four_panel_layout``)."""
    return linked_panels_canvas(scenario, four_panel_layout(), **options)  # type: ignore[arg-type]


def five_panel_canvas(
    scenario: Scenario,
    *,
    islm_rows: int = 3,
    adas_rows: int = 3,
    labor_rows: int = 3,
    lower_rows: int = 3,
    **options: object,
) -> CanvasGrid:
    """The four panels plus IS-LM above AD-AS in the right column (see ``five_panel_layout``)."""
    layout = five_panel_layout(
        islm_rows=islm_rows, adas_rows=adas_rows, labor_rows=labor_rows, lower_rows=lower_rows
    )
    return linked_panels_canvas(scenario, layout, **options)  # type: ignore[arg-type]
