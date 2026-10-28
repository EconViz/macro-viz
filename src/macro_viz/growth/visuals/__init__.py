"""Solow growth figures: production function, steady state, golden rule, and time paths."""

from __future__ import annotations

from macro_viz.growth.visuals._preset import (
    CONVERGENCE_HEIGHT_SHARE,
    CONVERGENCE_SPAN_SHARE,
    GOLDEN_SAMPLES_FLOOR,
    PATH_HEADROOM,
    SOLOW_EXTENT,
)
from macro_viz.growth.visuals.golden_rule import golden_rule_canvas
from macro_viz.growth.visuals.paths import (
    solow_growth_rate_canvas,
    solow_level_path_canvas,
    solow_log_path_canvas,
)
from macro_viz.growth.visuals.steady_state import production_function_canvas, solow_canvas

__all__ = [
    "CONVERGENCE_HEIGHT_SHARE",
    "CONVERGENCE_SPAN_SHARE",
    "SOLOW_EXTENT",
    "PATH_HEADROOM",
    "GOLDEN_SAMPLES_FLOOR",
    "production_function_canvas",
    "solow_canvas",
    "golden_rule_canvas",
    "solow_level_path_canvas",
    "solow_log_path_canvas",
    "solow_growth_rate_canvas",
]
