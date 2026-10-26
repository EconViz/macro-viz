"""Tick labels, their leaning and the placement of curve names beside them."""

from __future__ import annotations

from collections.abc import Callable, Collection, Sequence
from dataclasses import dataclass

from mosaickit import (
    Layer,
    TextLayer,
)

from macro_viz.errors import ValidationError
from macro_viz.panels import (
    Hop,
    PanelLayout,
    PanelSpec,
    PanelState,
)
from macro_viz.panels.curves import (
    KEY_DIGITS,
)
from macro_viz.panels.layout import X_AXIS
from macro_viz.visuals._placement import (
    Box,
    Placed,
    PlacementOptions,
    Scene,
    is_free,
    text_box,
)
from macro_viz.visuals.panels._context import _Context, _present
from macro_viz.visuals.panels._preset import POINTS_PER_INCH, TICK_CLEARANCE, TICK_OFFSET


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
