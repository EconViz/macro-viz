"""Linked-panel derivation of aggregate supply."""

from __future__ import annotations

import string
from collections.abc import Mapping

from mosaickit import CanvasGrid, MarkerLayer
from mosaickit.canvas.grid_link import GridLink

from macro_viz.errors import ValidationError
from macro_viz.panels import PanelLayout, PanelSpec, Scenario, Step, Tick
from macro_viz.panels.layout import ADAS, LABOR, PRODUCTION, X_AXIS, Y_AXIS
from macro_viz.panels.model import N, P, W, Y
from macro_viz.transmission import ASDerivation
from macro_viz.visuals.panels import PANEL_WIDTH, PanelGrid, linked_panels_canvas


def _as_layout() -> PanelLayout:
    panels = (
        PanelSpec("labor", LABOR, N, W, 0, 0),
        PanelSpec("production", PRODUCTION, N, Y, 1, 0, points=False),
        PanelSpec("as", ADAS, Y, P, 1, 1),
    )
    ticks = (
        Tick("labor", X_AXIS, N),
        Tick("labor", Y_AXIS, W),
        Tick("as", X_AXIS, Y),
        Tick("as", Y_AXIS, P),
    )
    return PanelLayout(panels, (), ticks)


def as_derivation_canvas(
    derivation: ASDerivation,
    *,
    title: str | None = None,
    labels: Mapping[str, str] | None = None,
    width: float = PANEL_WIDTH,
    **options: object,
) -> CanvasGrid:
    """Draw the labour market, production function, and the AS curve as one solved chain."""
    names = string.ascii_uppercase + string.ascii_lowercase
    if len(derivation.prices) > len(names):
        raise ValidationError(f"an AS derivation supports at most {len(names)} price levels")
    scenario = Scenario(
        derivation.economy,
        tuple(Step(names[index], price=price) for index, price in enumerate(derivation.prices)),
    )
    grid = linked_panels_canvas(
        scenario,
        _as_layout(),
        title=title,
        labels=labels,
        ad=False,
        sras=True,
        shifted_sras=False,
        width=width,
        **options,  # type: ignore[arg-type]
    )
    assert isinstance(grid, PanelGrid)
    labor, production, aggregate_supply = (item.canvas for item in grid.placements)
    for index, state in enumerate(derivation.states):
        production.add(
            MarkerLayer(
                ((state.employment, state.output),),
                id=f"macro.transmission.as.production.equilibrium.{index}",
                role="macro.point",
                z_index=6,
            )
        )
    links: list[GridLink] = []
    for state in derivation.states:
        links.extend(
            (
                GridLink(
                    0,
                    (state.employment, state.wage),
                    1,
                    (state.employment, state.output),
                    role="macro.link",
                ),
                GridLink(
                    1,
                    (state.employment, state.output),
                    2,
                    (state.output, state.price),
                    role="macro.link",
                ),
            )
        )
    return PanelGrid(
        ((labor, production, aggregate_supply),),
        rows=1,
        cols=3,
        links=links,
        column_gap=grid.column_gap,
        row_gap=grid.row_gap,
        outer=grid.outer,
    )
