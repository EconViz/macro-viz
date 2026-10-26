"""Linked-panel diagrams: several panels on one mosaickit grid, joined by dashed projections.

Every panel is an ordinary canvas whose axes show a solved variable over the same length as
every other panel that shows that variable, so a value read in one panel lands on the same pixel
column (or row) in the next. The dashed paths are ``GridLink`` objects drawn from data
coordinates, never from positions typed in. Curves, points, ticks and arrows come from
``macro_viz.panels`` and are drawn with the ``macro.*`` theme roles; all text is looked up in
the locale table."""

from __future__ import annotations

from macro_viz.visuals._labels import UPPER_RIGHT_TAIL_LABELS
from macro_viz.visuals.panels._geometry import _rotation_arrows
from macro_viz.visuals.panels._preset import (
    COLUMN_GAP,
    DEFAULT_EXTENT,
    DEFAULT_PAD,
    DIAGONAL_REACH,
    LABEL_GAP,
    MARGIN,
    OUTER_MARGIN,
    PANEL_WIDTH,
    ROW_GAP,
    SYMBOL_IDS,
    TOP_PAD,
)
from macro_viz.visuals.panels.builders import (
    five_panel_canvas,
    four_panel_canvas,
    linked_panels_canvas,
)

__all__ = [
    "COLUMN_GAP",
    "OUTER_MARGIN",
    "ROW_GAP",
    "PANEL_WIDTH",
    "DEFAULT_EXTENT",
    "DEFAULT_PAD",
    "TOP_PAD",
    "MARGIN",
    "LABEL_GAP",
    "UPPER_RIGHT_TAIL_LABELS",
    "SYMBOL_IDS",
    "DIAGONAL_REACH",
    "_rotation_arrows",
    "linked_panels_canvas",
    "four_panel_canvas",
    "five_panel_canvas",
]
