"""Linked-panel diagrams: several panels on one mosaickit grid, joined by dashed projections.

Every panel is an ordinary canvas whose axes show a solved variable over the same length as
every other panel that shows that variable, so a value read in one panel lands on the same pixel
column (or row) in the next. The dashed paths are ``GridLink`` objects drawn from data
coordinates, never from positions typed in. Curves, points, ticks and arrows come from
``macro_viz.panels`` and are drawn with the ``macro.*`` theme roles; all text is looked up in
the locale table.
"""

from __future__ import annotations

from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass

from mosaickit import (
    ArrowPlacement,
    ArrowStyle,
    Canvas,
    CanvasGrid,
    Layer,
    PathLayer,
    Span,
    Stroke,
    TextLayer,
)
from mosaickit.canvas.grid_link import GridLink

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
from macro_viz.panels.curves import DEFAULT_SAMPLES, KEY_DIGITS, CurveSpec, Subscripted
from macro_viz.panels.layout import DIAGONAL, X_AXIS
from macro_viz.panels.model import N, P, R, W, Y
from macro_viz.visuals._kit import axes_layers, canvas_spec, new_canvas
from macro_viz.visuals._theory import marked_point

GRID_GAP = 0.2
"""The gap mosaickit leaves between grid cells, as a share of a cell."""

PANEL_WIDTH = 4.3
"""Width in inches of one grid column."""

DEFAULT_EXTENT = 1.7
"""Axis length as a multiple of the largest solved value shown on it."""

DEFAULT_PAD = {N: 0.35, Y: 0.35, W: 0.1, P: 0.1, R: 0.1}
"""Room right of (and above) each variable's axis for curve names, as a share of its length."""

MARGIN = 0.14
"""Room under and left of each axis for tick labels, as a share of the axis length."""

TICK_CLEARANCE = 0.1
"""Tick labels closer than this share of the panel's range lean away from each other."""

LABEL_GAP = 0.13
"""How much of a panel's height a dashed path stops short of a tick label under an axis."""

SYMBOL_IDS = {
    N: "panels.var.employment",
    W: "panels.var.wage",
    Y: "panels.var.output",
    P: "panels.var.price",
    R: "panels.var.rate",
}
"""The locale id of each variable's symbol."""

TICK_OFFSET = 4.0
"""Distance in points between an axis and its tick label."""

DIAGONAL_REACH = 0.97
"""The share of the axis the 45-degree line runs before its arrowhead."""

ARROW = Stroke(arrow=ArrowStyle.TRIANGLE)


@dataclass(frozen=True, slots=True)
class _Context:
    layout: PanelLayout
    states: Sequence[PanelState]
    lengths: Mapping[str, float]
    pad: Mapping[str, float]
    labels: Labels
    margin: float

    def symbol(self, variable: str) -> str:
        return self.labels(SYMBOL_IDS[variable])

    def subscripted(self, value: Subscripted | int) -> str:
        if isinstance(value, int):
            return str(value)
        text = self.labels(f"panels.var.{value.symbol}")
        return text if value.index is None else f"{text}_{value.index}"

    def _range(self, variable: str) -> tuple[float, float]:
        length = self.lengths[variable]
        return (-self.margin * length, length * (1 + self.pad[variable]))

    def x_range(self, panel: PanelSpec) -> tuple[float, float]:
        return self._range(panel.x)

    def y_range(self, panel: PanelSpec) -> tuple[float, float]:
        return self._range(panel.y)


def _present(state: PanelState, panel: PanelSpec) -> bool:
    return panel.x in state.values and panel.y in state.values


def _unit_height(layout: PanelLayout, width: float) -> float:
    """Height of one grid row that makes the 45-degree panel square (else rows as wide)."""
    reference = next((p for p in layout.panels if p.kind == DIAGONAL), None)
    if reference is None:
        return width

    def span(units: int) -> float:
        return units + GRID_GAP * (units - 1)

    cols, rows = layout.cols, layout.rows
    cell_width = width * cols / span(cols)
    row_height = cell_width * span(reference.cols) / span(reference.rows)
    return row_height * span(rows) / rows


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
    return TextLayer(
        position,
        text,
        id=layer_id,
        role="macro.mark",
        anchor="right",
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


def _panel_canvas(
    ctx: _Context,
    panel: PanelSpec,
    curves: Sequence[CurveSpec],
    arrows: Sequence[Layer],
    ticks: Sequence[Layer],
    pieces: Sequence[tuple[tuple[float, float], tuple[float, float]]],
    title: str | None,
    steps: Collection[str],
    width: float,
    height: float,
) -> Canvas:
    x_range, y_range = ctx.x_range(panel), ctx.y_range(panel)
    spec = canvas_spec(
        x_range, y_range, width=panel.cols * width, height=panel.rows * height, title=title
    )
    canvas = new_canvas(spec)
    canvas.extend(
        axes_layers(
            (0.0, ctx.lengths[panel.x]),
            (0.0, ctx.lengths[panel.y]),
            x_label=f"${ctx.symbol(panel.x)}$",
            y_label=f"${ctx.symbol(panel.y)}$",
            origin_label=ctx.labels("axis.origin"),
        )
    )
    if panel.kind == DIAGONAL:
        tip = DIAGONAL_REACH * min(ctx.lengths[panel.x], ctx.lengths[panel.y])
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
    counts: dict[str, int] = {}
    for curve in curves:
        number = counts.get(curve.family, 0)
        counts[curve.family] = number + 1
        base = f"macro.panels.{panel.key}.{curve.family}.{number}"
        role = "macro.curve.panel" if curve.main else "macro.curve.panel.shifted"
        canvas.add(PathLayer(curve.points, id=base, role=role, z_index=2))
        fields = {name: ctx.subscripted(value) for name, value in curve.fields.items()}
        from mosaickit import PointLabelLayer

        canvas.add(
            PointLabelLayer(
                curve.end,
                ctx.labels(curve.label_id, **fields),
                id=f"{base}.label",
                role=role,
                z_index=7,
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
    canvas.extend(arrows)
    canvas.extend(ticks)
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
            canvas.extend(
                marked_point(
                    location,
                    f"${state.label}$",
                    layer_id=f"macro.panels.{panel.key}.point.{state.label}",
                )
            )
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
    pad: Mapping[str, float] | None = None,
    margin: float = MARGIN,
    samples: int = DEFAULT_SAMPLES,
    label_gap: float = LABEL_GAP,
    width: float = PANEL_WIDTH,
) -> CanvasGrid:
    """Draw ``scenario`` on ``layout``: curves, points, ticks, shift arrows and projections.

    ``mode`` draws curves from the equations (``DERIVED``) or as lines through the solved
    points (``SCHEMATIC``). ``sras``, ``lras`` and ``ad`` choose the curves of the AD-AS panel
    (``shifted_sras`` False keeps only the first step's SRAS).

    ``steps`` limits which steps are marked and projected (default all); ``projections``
    limits which projections are drawn, by name; ``hide_ticks`` is a collection of
    ``(variable, step label)`` pairs whose tick label is left out; ``ranges`` fixes the axis
    length of a variable; ``pad`` the room right of each axis for curve names (share of its
    length); ``margin`` the room under and left of the axes for tick labels; ``label_gap`` how
    far dashed paths stop short of a tick label. ``title`` is drawn above the top-left panel;
    ``None`` draws none.
    """
    text = Labels(labels)
    states = scenario.solve()
    shown = {state.label for state in states} if steps is None else set(steps)
    unknown = sorted(shown - {state.label for state in states})
    if unknown:
        raise ValidationError(f"unknown steps: {unknown}")
    lengths = axis_lengths(states, extent=extent, overrides=ranges, natural=lras)
    full_pad = {**DEFAULT_PAD, **(pad or {})}
    ctx = _Context(layout, states, lengths.lengths, full_pad, text, margin)
    options = CurveOptions(
        mode=mode, samples=samples, sras=sras, shifted_sras=shifted_sras, lras=lras, ad=ad
    )
    arrow_options = shift_arrows_on if isinstance(shift_arrows_on, ArrowOptions) else ArrowOptions()
    ticks, drawn = _ticks(ctx, hide_ticks)
    height = _unit_height(layout, width)
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
        curves = curve_specs(panel, scenario, states, lengths, options)
        arrows: list[Layer] = []
        if shift_arrows_on is not False:
            for number, arrow in enumerate(
                shift_arrows(panel, curves, states, dict(lengths.lengths), arrow_options)
            ):
                arrows.append(
                    PathLayer(
                        arrow.points,
                        id=f"macro.panels.{panel.key}.shift.{number}",
                        role="macro.shift",
                        stroke=ARROW,
                        arrow_placement=ArrowPlacement.END,
                        z_index=5,
                    )
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
    return CanvasGrid(rows, rows=layout.rows, cols=layout.cols, links=links)


def four_panel_canvas(scenario: Scenario, **options: object) -> CanvasGrid:
    """Labour market, AD-AS, production function and 45-degree line (see ``four_panel_layout``)."""
    return linked_panels_canvas(scenario, four_panel_layout(), **options)  # type: ignore[arg-type]


def five_panel_canvas(
    scenario: Scenario,
    *,
    islm_rows: int = 2,
    adas_rows: int = 2,
    labor_rows: int = 3,
    lower_rows: int = 3,
    **options: object,
) -> CanvasGrid:
    """The four panels plus IS-LM above AD-AS in the right column (see ``five_panel_layout``)."""
    layout = five_panel_layout(
        islm_rows=islm_rows, adas_rows=adas_rows, labor_rows=labor_rows, lower_rows=lower_rows
    )
    return linked_panels_canvas(scenario, layout, **options)  # type: ignore[arg-type]
