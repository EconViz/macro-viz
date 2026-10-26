"""Shared geometry and layout helpers for transmission derivations."""

from __future__ import annotations

from collections.abc import Sequence

from mosaickit import Canvas, CanvasGrid, Span
from mosaickit.canvas.grid_link import GridLink
from mosaickit.layout import clip_polyline, data_slope_for_display, extend_line_through

from macro_viz.errors import ValidationError
from macro_viz.visuals._theory import HEADROOM, trim
from macro_viz.visuals.panels import PanelGrid
from macro_viz.visuals.transmission._preset import (
    DERIVED_TAIL,
    GRID_COLUMN_GAP,
    GRID_OUTER,
    GRID_ROW_GAP,
    LIQUIDITY_DISPLAY_SLOPE,
    LIQUIDITY_TAIL_SHARE,
)


def indexed(label: str, index: int) -> str:
    if label.startswith("$") and label.endswith("$"):
        return f"{label[:-1]}_{index}$"
    return f"{label}_{index}"


def called(label: str, argument: str) -> str:
    return f"${label.strip('$')}({argument.strip('$')})$"


def line_through(
    points: Sequence[tuple[float, float]], x_max: float, y_max: float
) -> list[tuple[float, float]]:
    """Extend the chord through solved points to the visible edges of its panel."""
    first, last = sorted(points)[0], sorted(points)[-1]
    run = last[0] - first[0]
    if abs(run) < 1e-12:
        raise ValidationError("a derived curve needs distinct horizontal values")
    slope = (last[1] - first[1]) / run
    intercept = first[1] - slope * first[0]
    return trim(((0.0, intercept), (x_max, intercept + slope * x_max)), x_max, y_max)


def tailed_line(
    points: Sequence[tuple[float, float]], x_max: float, y_max: float, tail_share: float
) -> list[tuple[float, float]]:
    """Extend the chord by a share of its solved span instead of to the panel edges."""
    chord = extend_line_through(sorted(points), before=tail_share)
    return list(clip_polyline(chord, (0.0, HEADROOM * x_max), (0.0, HEADROOM * y_max)))


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


def grid(
    cells: Sequence[Sequence[Canvas | Span | None]],
    links: Sequence[GridLink],
    *,
    rows: int,
    cols: int,
) -> CanvasGrid:
    return PanelGrid(
        cells,
        rows=rows,
        cols=cols,
        links=links,
        column_gap=GRID_COLUMN_GAP,
        row_gap=GRID_ROW_GAP,
        outer=GRID_OUTER,
    )
