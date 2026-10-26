"""Aggregate supply and aggregate demand figures."""

from __future__ import annotations

from macro_viz.visuals.adas._curves import demand_curve, supply_curve
from macro_viz.visuals.adas._preset import (
    AMBIGUOUS_SPAN_SHARE,
    DEMAND_FLOOR_SHARE,
    LABEL_GAP,
    MARKED_OUTPUTS,
    SAME_OUTPUT,
    SHIFT_ARROW_SHARE,
)
from macro_viz.visuals.adas.adjustment import adas_adjustment_canvas
from macro_viz.visuals.adas.model import adas_canvas
from macro_viz.visuals.adas.supply_demand import aggregate_demand_canvas, aggregate_supply_canvas

__all__ = [
    "SHIFT_ARROW_SHARE",
    "AMBIGUOUS_SPAN_SHARE",
    "DEMAND_FLOOR_SHARE",
    "MARKED_OUTPUTS",
    "SAME_OUTPUT",
    "LABEL_GAP",
    "supply_curve",
    "demand_curve",
    "aggregate_supply_canvas",
    "aggregate_demand_canvas",
    "adas_canvas",
    "adas_adjustment_canvas",
]
