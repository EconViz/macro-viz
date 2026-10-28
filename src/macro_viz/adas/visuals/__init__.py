"""Aggregate supply and aggregate demand figures."""

from __future__ import annotations

from macro_viz.adas.visuals._curves import demand_curve, supply_curve
from macro_viz.adas.visuals._preset import (
    AMBIGUOUS_SPAN_SHARE,
    DEMAND_FLOOR_SHARE,
    LABEL_GAP,
    MARKED_OUTPUTS,
    SAME_OUTPUT,
    SHIFT_ARROW_SHARE,
)
from macro_viz.adas.visuals.adjustment import adas_adjustment_canvas
from macro_viz.adas.visuals.derivation.ad import ad_derivation_canvas
from macro_viz.adas.visuals.derivation.as_derivation import as_derivation_canvas
from macro_viz.adas.visuals.model import adas_canvas
from macro_viz.adas.visuals.supply_demand import aggregate_demand_canvas, aggregate_supply_canvas

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
    "ad_derivation_canvas",
    "as_derivation_canvas",
]
