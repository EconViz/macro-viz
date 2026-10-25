"""Which panels a linked diagram has, where they sit, and how a value travels between them.

A ``PanelLayout`` is data: panels with grid cells, the variables on their axes, the ``Tick``
marks where a value is read on an axis, and ``Projection`` paths that carry a solved value from
one panel to the next. Two panels that show the same variable on an axis use one range for it
(see ``macro_viz.visuals.panels``), so a vertical path between panels that share ``x`` (or a
horizontal path between panels that share ``y``) is exact by construction; the layout checks
that such panels share their grid columns (or rows).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from macro_viz.errors import ValidationError
from macro_viz.panels.model import N, P, R, W, Y

LABOR, PRODUCTION, ADAS, ISLM, DIAGONAL = "labor", "production", "adas", "islm", "diagonal"
"""Kinds of panel: each has its own curves in ``macro_viz.panels.curves``."""

X_AXIS, Y_AXIS = "x", "y"


@dataclass(frozen=True, slots=True)
class PanelSpec:
    """A panel: its kind, the variables on its axes, and its cell in the grid.

    ``rows`` and ``cols`` are spans in grid units (a panel two units tall is twice as high,
    plus the gap between them).
    """

    key: str
    kind: str
    x: str
    y: str
    row: int
    col: int
    rows: int = 1
    cols: int = 1
    points: bool = True


@dataclass(frozen=True, slots=True)
class Hop:
    """A point of a projection path in ``panel``; a variable gives the coordinate, ``None``
    puts the point on that axis (coordinate zero). ``cleared`` marks a point on an axis where
    a tick label sits: the path stops short of the label when the tick is drawn."""

    panel: str
    x: str | None
    y: str | None
    cleared: bool = False


@dataclass(frozen=True, slots=True)
class Projection:
    """Dashed paths that carry the solved values of a step from panel to panel."""

    name: str
    paths: tuple[tuple[Hop, ...], ...]


@dataclass(frozen=True, slots=True)
class Tick:
    """A label of ``variable`` on the ``axis`` of ``panel``, one per distinct solved value."""

    panel: str
    axis: str
    variable: str


@dataclass(frozen=True, slots=True)
class PanelLayout:
    """The panels, their projections and their ticks."""

    panels: tuple[PanelSpec, ...]
    projections: tuple[Projection, ...]
    ticks: tuple[Tick, ...]

    def __post_init__(self) -> None:
        keys = [panel.key for panel in self.panels]
        if len(set(keys)) != len(keys):
            raise ValidationError("panel keys must be distinct")
        taken: dict[tuple[int, int], str] = {}
        for panel in self.panels:
            if min(panel.row, panel.col) < 0 or min(panel.rows, panel.cols) < 1:
                raise ValidationError(f"panel {panel.key!r} has a bad cell")
            for r in range(panel.row, panel.row + panel.rows):
                for c in range(panel.col, panel.col + panel.cols):
                    if (r, c) in taken:
                        raise ValidationError(f"panels {taken[(r, c)]!r} and {panel.key!r} overlap")
                    taken[(r, c)] = panel.key
        for tick in self.ticks:
            self.panel(tick.panel)
        for projection in self.projections:
            for path in projection.paths:
                for first, second in zip(path, path[1:], strict=False):
                    self._check_hop(first, second)

    def panel(self, key: str) -> PanelSpec:
        for panel in self.panels:
            if panel.key == key:
                return panel
        raise ValidationError(f"no panel called {key!r}")

    @property
    def rows(self) -> int:
        return max(panel.row + panel.rows for panel in self.panels)

    @property
    def cols(self) -> int:
        return max(panel.col + panel.cols for panel in self.panels)

    def _check_hop(self, first: Hop, second: Hop) -> None:
        if first.panel == second.panel:
            return
        a, b = self.panel(first.panel), self.panel(second.panel)
        if first.x is not None and first.x == second.x:
            if (a.col, a.cols) != (b.col, b.cols) or a.x != b.x:
                raise ValidationError(
                    f"{a.key!r} and {b.key!r} must share their columns and x axis"
                )
        elif first.y is not None and first.y == second.y:
            if (a.row, a.rows) != (b.row, b.rows) or a.y != b.y:
                raise ValidationError(f"{a.key!r} and {b.key!r} must share their rows and y axis")
        else:
            raise ValidationError(f"a path from {a.key!r} to {b.key!r} must keep x or y")

    def without(self, *panels: str) -> PanelLayout:
        """The layout minus some panels, with the projections and ticks that touch them."""
        for key in panels:
            self.panel(key)
        kept = tuple(panel for panel in self.panels if panel.key not in panels)
        projections = tuple(
            projection
            for projection in self.projections
            if all(hop.panel not in panels for path in projection.paths for hop in path)
        )
        ticks = tuple(tick for tick in self.ticks if tick.panel not in panels)
        return PanelLayout(kept, projections, ticks)


def _paths(*paths: Sequence[Hop]) -> tuple[tuple[Hop, ...], ...]:
    return tuple(tuple(path) for path in paths)


def four_panel_layout() -> PanelLayout:
    """Labour market and AD-AS above, production function and 45-degree line below."""
    panels = (
        PanelSpec("labor", LABOR, N, W, 0, 0),
        PanelSpec("adas", ADAS, Y, P, 0, 1),
        PanelSpec("production", PRODUCTION, N, Y, 1, 0, points=False),
        PanelSpec("diagonal", DIAGONAL, Y, Y, 1, 1, points=False),
    )
    projections = (
        Projection(
            N, _paths((Hop("labor", N, W), Hop("labor", N, None, True), Hop("production", N, Y)))
        ),
        Projection(W, _paths((Hop("labor", None, W), Hop("labor", N, W)))),
        Projection(
            Y,
            _paths(
                (Hop("production", N, Y), Hop("diagonal", None, Y), Hop("diagonal", Y, Y)),
                (Hop("diagonal", Y, Y), Hop("adas", Y, None, True), Hop("adas", Y, P)),
            ),
        ),
        Projection(P, _paths((Hop("adas", None, P), Hop("adas", Y, P)))),
    )
    ticks = (
        Tick("labor", X_AXIS, N),
        Tick("labor", Y_AXIS, W),
        Tick("adas", X_AXIS, Y),
        Tick("adas", Y_AXIS, P),
    )
    return PanelLayout(panels, projections, ticks)


def five_panel_layout(
    *, islm_rows: int = 3, adas_rows: int = 3, labor_rows: int = 3, lower_rows: int = 3
) -> PanelLayout:
    """The four panels with IS-LM above AD-AS, so the right column shares one ``Y`` axis.

    The row spans (grid units) may be overridden together, but default to equal-sized axes in
    every panel.  The grid has an empty cell above the labour market.
    """
    top = islm_rows
    middle = max(adas_rows, labor_rows)
    panels = (
        PanelSpec("islm", ISLM, Y, R, 0, 1, rows=islm_rows),
        PanelSpec("labor", LABOR, N, W, top, 0, rows=labor_rows),
        PanelSpec("adas", ADAS, Y, P, top, 1, rows=adas_rows),
        PanelSpec("production", PRODUCTION, N, Y, top + middle, 0, rows=lower_rows, points=False),
        PanelSpec("diagonal", DIAGONAL, Y, Y, top + middle, 1, rows=lower_rows, points=False),
    )
    base = four_panel_layout()
    projections = base.projections + (
        Projection(
            R,
            _paths((Hop("islm", None, R), Hop("islm", Y, R))),
        ),
        Projection(
            f"{Y}.{R}",
            _paths((Hop("islm", Y, R), Hop("islm", Y, None, True), Hop("adas", Y, P))),
        ),
    )
    ticks = base.ticks + (Tick("islm", X_AXIS, Y), Tick("islm", Y_AXIS, R))
    return PanelLayout(panels, projections, ticks)
