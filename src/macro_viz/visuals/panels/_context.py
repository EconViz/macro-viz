"""The window and the shared context a linked-panel figure is drawn in."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from macro_viz.i18n import Labels
from macro_viz.panels import (
    CurveOptions,
    PanelLayout,
    PanelSpec,
    PanelState,
)
from macro_viz.panels.curves import (
    CurveSpec,
    Ranges,
    Subscripted,
    clip,
)
from macro_viz.panels.layout import DIAGONAL
from macro_viz.panels.model import N, Y
from macro_viz.visuals.panels._preset import SYMBOL_IDS


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
