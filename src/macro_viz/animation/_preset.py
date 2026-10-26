"""Defaults and constants of the animation exporters."""

from __future__ import annotations

from collections.abc import Callable

from mosaickit import (
    Canvas,
    CanvasGrid,
)
from mosaickit.styles import DashStyle

Builder = Callable[[float], Canvas | CanvasGrid]
"""A function from a parameter value to the canvas drawing the figure at that value."""

DEFAULT_FPS = 12
DEFAULT_DPI = 150
DEFAULT_STEP_SECONDS = 0.8
"""Seconds KineticKit takes to morph from one frame to the next in an animated SVG."""

POINTS_PER_INCH = 72.0
MARGIN_POINTS = (46.0, 40.0, 60.0, 34.0)
"""Left, bottom, right, and top space around the axes in an animated SVG, in points."""

DASH_PATTERNS = {
    DashStyle.DASHED: (5.0, 3.0),
    DashStyle.DOTTED: (1.0, 3.0),
    DashStyle.DASHDOT: (5.0, 3.0, 1.0, 3.0),
}
"""Dash and gap lengths in multiples of the line width, per dash style."""

ARROW_HEAD_LENGTH = 8.0
ARROW_HEAD_HALF_WIDTH = 3.4
"""Arrowhead length and half width in multiples of the line width."""

LABEL_GAP = 5.0
"""Gap in points between a point and the label an animated SVG places beside it."""

LABEL_CORNERS = (("left", "bottom"), ("right", "bottom"), ("left", "top"), ("right", "top"))
"""Where a point label may sit relative to its point, in order of preference."""

DEFAULT_TEXT_SIZE = 11.0
"""Font size in points of a label whose theme role names none."""

DEFAULT_MARKER_AREA = 36.0
"""Area in square points of a marker whose theme role names no size."""

SEGMENT_SAMPLES = 12
"""How many points along a line are tested when a label is placed beside it."""

BASELINE_SHARE = {"top": 0.78, "center": 0.34, "bottom": 0.0}
"""Where the baseline sits below the anchor, as a share of the font size, per vertical anchor."""
