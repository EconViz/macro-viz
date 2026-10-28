"""Shared geometry and layout helpers for transmission derivations."""

from __future__ import annotations

from collections.abc import Sequence

from mosaickit import Canvas, CanvasGrid, GridSpacing, Span
from mosaickit.canvas.grid_link import GridLink
from mosaickit.layout import data_slope_for_display

from macro_viz.core.errors import ValidationError
from macro_viz.visuals._theory import HEADROOM, trim
from macro_viz.visuals.derivation._preset import (
    DERIVED_TAIL,
    GRID_COLUMN_GAP,
    GRID_OUTER,
    GRID_ROW_GAP,
    ID_ROOT,
    LIQUIDITY_DISPLAY_SLOPE,
    LIQUIDITY_TAIL_SHARE,
    MIN_RUN,
)


def layer_id(figure: str, *parts: object) -> str:
    """``macro.transmission.<figure>.<part>...``: the stable id of one layer of a derivation."""
    return ".".join((ID_ROOT, figure, *(str(part) for part in parts)))


def called(label: str, argument: str) -> str:
    return f"${label.strip('$')}({argument.strip('$')})$"


def line_through(
    points: Sequence[tuple[float, float]], x_max: float, y_max: float
) -> list[tuple[float, float]]:
    """Extend the chord through solved points to the visible edges of its panel."""
    first, last = sorted(points)[0], sorted(points)[-1]
    run = last[0] - first[0]
    if abs(run) < MIN_RUN:
        raise ValidationError("a derived curve needs distinct horizontal values")
    slope = (last[1] - first[1]) / run
    intercept = first[1] - slope * first[0]
    return trim(((0.0, intercept), (x_max, intercept + slope * x_max)), x_max, y_max)


def parallel_liquidity_schedule(
    equilibrium: tuple[float, float],
    x_max: float,
    y_max: float,
    width: float,
    height: float,
) -> list[tuple[float, float]]:
    """A parallel falling schedule with a fixed screen slope through ``equilibrium``."""
    data_slope = -data_slope_for_display(LIQUIDITY_DISPLAY_SLOPE, x_max, y_max, width, height)
    x, y = equilibrium
    reach = LIQUIDITY_TAIL_SHARE * x_max
    return trim(
        ((x - reach, y - data_slope * reach), (x + reach, y + data_slope * reach)),
        x_max,
        y_max,
    )


def axis_with_upper_tail(values: Sequence[float]) -> float:
    """Place the largest solved value below the plot edge so a line can continue past it."""
    low, high = min(values), max(values)
    return (high + DERIVED_TAIL * (high - low)) / HEADROOM


SPACING = GridSpacing(column_gap=GRID_COLUMN_GAP, row_gap=GRID_ROW_GAP, outer=GRID_OUTER)
"""The gaps between the panels of a derivation, shares of a cell."""


def grid(
    cells: Sequence[Sequence[Canvas | Span | None]],
    links: Sequence[GridLink],
    *,
    rows: int,
    cols: int,
) -> CanvasGrid:
    return CanvasGrid(
        cells,
        rows=rows,
        cols=cols,
        links=links,
        spacing=SPACING,
    )
