"""Linked-panel derivation of aggregate supply."""

from __future__ import annotations

import string
from collections.abc import Mapping

from mosaickit import CanvasGrid

from macro_viz.errors import ValidationError
from macro_viz.panels import Scenario, Step
from macro_viz.panels.layout import four_panel_layout
from macro_viz.transmission import ASDerivation
from macro_viz.visuals.panels import PANEL_WIDTH, linked_panels_canvas


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
    return linked_panels_canvas(
        scenario,
        four_panel_layout(),
        title=title,
        labels=labels,
        ad=False,
        sras=True,
        shifted_sras=False,
        width=width,
        **options,  # type: ignore[arg-type]
    )
