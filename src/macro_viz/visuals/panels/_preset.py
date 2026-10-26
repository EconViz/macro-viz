"""Defaults and constants of the linked-panel diagrams."""

from __future__ import annotations

from mosaickit import (
    ArrowStyle,
    Stroke,
)

from macro_viz.panels.model import N, P, R, W, Y

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

DIAGONAL_REACH = 0.97
"""The share of the axis the 45-degree line runs before its arrowhead."""

ARROW = Stroke(arrow=ArrowStyle.TRIANGLE)

ROTATION_SAMPLES = 48
"""Sampling resolution for a Bézier marker; placement and curvature do not depend on it."""
