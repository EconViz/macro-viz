"""Linked-panel diagrams: typed blocks, scenarios, and the layout that links their panels."""

from macro_viz.panels.arrows import ArrowOptions, ShiftArrow, shift_arrows
from macro_viz.panels.curves import CurveOptions, CurveSpec, Mode, Ranges, axis_lengths, curve_specs
from macro_viz.panels.layout import (
    Hop,
    PanelLayout,
    PanelSpec,
    Projection,
    Tick,
    five_panel_layout,
    four_panel_layout,
)
from macro_viz.panels.model import (
    IsLm,
    LinearFunction,
    MacroEconomy,
    QuadraticProduction,
    Shock,
)
from macro_viz.panels.scenario import IsLmSketch, PanelState, Scenario, Step

__all__ = [
    "ArrowOptions",
    "CurveOptions",
    "CurveSpec",
    "Hop",
    "IsLm",
    "IsLmSketch",
    "LinearFunction",
    "MacroEconomy",
    "Mode",
    "PanelLayout",
    "PanelSpec",
    "PanelState",
    "Projection",
    "QuadraticProduction",
    "Ranges",
    "Scenario",
    "Shock",
    "ShiftArrow",
    "Step",
    "Tick",
    "axis_lengths",
    "curve_specs",
    "five_panel_layout",
    "four_panel_layout",
    "shift_arrows",
]
