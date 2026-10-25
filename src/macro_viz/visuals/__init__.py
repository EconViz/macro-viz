"""MosaicKit visual builders for typed macro-viz results."""

from macro_viz.visuals.accounts import (
    gdp_decomposition_canvas,
    gdp_deflator_canvas,
    gdp_levels_canvas,
    inflation_canvas,
    labor_market_canvas,
    price_index_canvas,
    unemployment_rate_canvas,
)
from macro_viz.visuals.cycles import business_cycle_canvas, output_gap_canvas
from macro_viz.visuals.keynesian import (
    consumption_function_canvas,
    keynesian_cross_canvas,
    multiplier_canvas,
)

__all__ = [
    "business_cycle_canvas",
    "consumption_function_canvas",
    "gdp_decomposition_canvas",
    "gdp_deflator_canvas",
    "gdp_levels_canvas",
    "inflation_canvas",
    "keynesian_cross_canvas",
    "labor_market_canvas",
    "multiplier_canvas",
    "output_gap_canvas",
    "price_index_canvas",
    "unemployment_rate_canvas",
]
