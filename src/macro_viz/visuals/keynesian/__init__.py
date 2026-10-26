"""Keynesian goods-market figures: consumption function, cross, and multiplier."""

from __future__ import annotations

from macro_viz.visuals.keynesian._preset import (
    LABEL_GAP,
    SHIFT_ARROW_POSITION,
    SLOPE_POSITION,
    SLOPE_RUN_SHARE,
)
from macro_viz.visuals.keynesian.consumption import consumption_function_canvas
from macro_viz.visuals.keynesian.cross import keynesian_cross_canvas
from macro_viz.visuals.keynesian.multiplier import multiplier_canvas
from macro_viz.visuals.keynesian.open_goods import open_goods_canvas

__all__ = [
    "LABEL_GAP",
    "SHIFT_ARROW_POSITION",
    "SLOPE_POSITION",
    "SLOPE_RUN_SHARE",
    "consumption_function_canvas",
    "keynesian_cross_canvas",
    "multiplier_canvas",
    "open_goods_canvas",
]
