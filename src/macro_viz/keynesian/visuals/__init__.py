"""Keynesian goods-market figures: consumption function, cross, and multiplier."""

from __future__ import annotations

from macro_viz.keynesian.visuals._preset import (
    LABEL_GAP,
    SHIFT_ARROW_POSITION,
    SLOPE_POSITION,
    SLOPE_RUN_SHARE,
)
from macro_viz.keynesian.visuals.consumption import consumption_function_canvas
from macro_viz.keynesian.visuals.cross import keynesian_cross_canvas
from macro_viz.keynesian.visuals.multiplier import multiplier_canvas


def __getattr__(name: str) -> object:
    if name == "open_goods_canvas":
        from macro_viz.open_economy.visuals.open_goods import open_goods_canvas

        return open_goods_canvas
    raise AttributeError(name)


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
