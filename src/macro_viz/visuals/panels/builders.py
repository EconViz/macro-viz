"""The public linked-panel figures."""

from __future__ import annotations

from collections.abc import Collection, Mapping

from mosaickit import (
    Canvas,
    CanvasGrid,
    GridSpacing,
    Span,
)
from mosaickit.canvas.grid_link import GridLink
from mosaickit.layout.labels import LabelOptions

from macro_viz.adas.linked import (
    ArrowOptions,
    CurveOptions,
    Mode,
    PanelLayout,
    Scenario,
    axis_lengths,
    curve_specs,
    five_panel_layout,
    four_panel_layout,
    shift_arrows,
)
from macro_viz.adas.linked.curves import (
    DEFAULT_SAMPLES,
)
from macro_viz.core.errors import ValidationError
from macro_viz.core.i18n import Labels
from macro_viz.visuals._labels import LABEL_OPTIONS
from macro_viz.visuals.panels._context import _aspect, _Context, _unit_height, _Window
from macro_viz.visuals.panels._geometry import _rotation_arrows, _shifted_states
from macro_viz.visuals.panels._panel import _panel_canvas
from macro_viz.visuals.panels._preset import (
    COLUMN_GAP,
    DEFAULT_EXTENT,
    DEFAULT_PAD,
    LABEL_GAP,
    MARGIN,
    OUTER_MARGIN,
    PANEL_WIDTH,
    ROW_GAP,
    TOP_PAD,
)
from macro_viz.visuals.panels._ticks import _axes_size_pt, _segments, _split, _ticks


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
    primary_demand_tail: float | None = None,
    pad: Mapping[str, float] | None = None,
    margin: float = MARGIN,
    top_pad: float = TOP_PAD,
    samples: int = DEFAULT_SAMPLES,
    label_gap: float = LABEL_GAP,
    column_gap: float = COLUMN_GAP,
    row_gap: float = ROW_GAP,
    outer: float = OUTER_MARGIN,
    label_options: LabelOptions = LABEL_OPTIONS,
    point_label_offset: tuple[float, float] | None = None,
    production_from_origin: bool = False,
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
    the outermost solved value. ``demand_tail`` does so for the left end of labour demand;
    ``primary_demand_tail`` may extend only its primary curve farther.

    ``pad`` is the room right of each horizontal axis for curve names and ``top_pad`` the room
    above each vertical axis (shares of the axis length); ``margin`` the room under and left of
    the axes for tick labels; ``label_gap`` how far dashed paths stop short of a tick label;
    ``column_gap`` and ``row_gap`` the space between grid columns and rows (shares of a cell);
    ``outer`` the margin around the figure (a share of its size); ``label_options`` the distances
    of the label placer (a MosaicKit ``LabelOptions``). ``point_label_offset`` fixes point names
    at that offset from their markers instead of asking the label placer to move them.
    ``production_from_origin`` extends production curves to the displayed origin.

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
        mode=mode,
        samples=samples,
        sras=sras,
        shifted_sras=shifted_sras,
        lras=lras,
        ad=ad,
        production_from_origin=production_from_origin,
    )
    window = _Window(corner, lengths.lengths, options.headroom)
    if corner:
        options = window.options(options, solved, tails or {}, demand_tail, primary_demand_tail)
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
            label_options,
            point_label_offset,
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
    return CanvasGrid(
        rows,
        rows=layout.rows,
        cols=layout.cols,
        links=links,
        spacing=GridSpacing(column_gap=column_gap, row_gap=row_gap, outer=outer),
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
