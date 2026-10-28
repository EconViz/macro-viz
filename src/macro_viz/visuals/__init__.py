"""Public figure builders, loaded when requested to avoid import cycles."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from macro_viz.adas.visuals import (
        ad_derivation_canvas,
        adas_adjustment_canvas,
        adas_canvas,
        aggregate_demand_canvas,
        aggregate_supply_canvas,
        as_derivation_canvas,
    )
    from macro_viz.growth.visuals import (
        golden_rule_canvas,
        production_function_canvas,
        solow_canvas,
        solow_growth_rate_canvas,
        solow_level_path_canvas,
        solow_log_path_canvas,
    )
    from macro_viz.islm.visuals import (
        is_derivation_canvas,
        islm_canvas,
        islm_expectations_canvas,
        lm_derivation_canvas,
    )
    from macro_viz.keynesian.visuals import (
        consumption_function_canvas,
        keynesian_cross_canvas,
        multiplier_canvas,
    )
    from macro_viz.labor.visuals import wsps_canvas
    from macro_viz.money.visuals import (
        central_bank_money_canvas,
        money_demand_canvas,
        money_market_canvas,
    )
    from macro_viz.open_economy.visuals import (
        interest_parity_canvas,
        open_goods_canvas,
        open_islm_canvas,
    )
    from macro_viz.visuals.panels import five_panel_canvas, four_panel_canvas, linked_panels_canvas

_MODULES = {
    "ad_derivation_canvas": "macro_viz.adas.visuals",
    "adas_adjustment_canvas": "macro_viz.adas.visuals",
    "adas_canvas": "macro_viz.adas.visuals",
    "aggregate_demand_canvas": "macro_viz.adas.visuals",
    "aggregate_supply_canvas": "macro_viz.adas.visuals",
    "as_derivation_canvas": "macro_viz.adas.visuals",
    "golden_rule_canvas": "macro_viz.growth.visuals",
    "production_function_canvas": "macro_viz.growth.visuals",
    "solow_canvas": "macro_viz.growth.visuals",
    "solow_growth_rate_canvas": "macro_viz.growth.visuals",
    "solow_level_path_canvas": "macro_viz.growth.visuals",
    "solow_log_path_canvas": "macro_viz.growth.visuals",
    "is_derivation_canvas": "macro_viz.islm.visuals",
    "islm_canvas": "macro_viz.islm.visuals",
    "islm_expectations_canvas": "macro_viz.islm.visuals",
    "lm_derivation_canvas": "macro_viz.islm.visuals",
    "consumption_function_canvas": "macro_viz.keynesian.visuals",
    "keynesian_cross_canvas": "macro_viz.keynesian.visuals",
    "multiplier_canvas": "macro_viz.keynesian.visuals",
    "wsps_canvas": "macro_viz.labor.visuals",
    "central_bank_money_canvas": "macro_viz.money.visuals",
    "money_demand_canvas": "macro_viz.money.visuals",
    "money_market_canvas": "macro_viz.money.visuals",
    "interest_parity_canvas": "macro_viz.open_economy.visuals",
    "open_goods_canvas": "macro_viz.open_economy.visuals",
    "open_islm_canvas": "macro_viz.open_economy.visuals",
    "five_panel_canvas": "macro_viz.visuals.panels",
    "four_panel_canvas": "macro_viz.visuals.panels",
    "linked_panels_canvas": "macro_viz.visuals.panels",
}

__all__ = [
    "interest_parity_canvas",
    "open_islm_canvas",
    "central_bank_money_canvas",
    "golden_rule_canvas",
    "production_function_canvas",
    "solow_canvas",
    "solow_growth_rate_canvas",
    "solow_level_path_canvas",
    "solow_log_path_canvas",
    "wsps_canvas",
    "adas_adjustment_canvas",
    "ad_derivation_canvas",
    "adas_canvas",
    "as_derivation_canvas",
    "aggregate_demand_canvas",
    "aggregate_supply_canvas",
    "consumption_function_canvas",
    "islm_canvas",
    "is_derivation_canvas",
    "islm_expectations_canvas",
    "five_panel_canvas",
    "four_panel_canvas",
    "keynesian_cross_canvas",
    "linked_panels_canvas",
    "lm_derivation_canvas",
    "money_demand_canvas",
    "money_market_canvas",
    "multiplier_canvas",
    "open_goods_canvas",
]


def __getattr__(name: str) -> Any:
    if name not in _MODULES:
        raise AttributeError(name)
    value = getattr(import_module(_MODULES[name]), name)
    globals()[name] = value
    return value
