"""Linked-panel derivation of aggregate supply."""

from __future__ import annotations

import string
from collections.abc import Mapping, Sequence
from typing import cast

from mosaickit import CanvasGrid

from macro_viz.errors import ValidationError
from macro_viz.panels import PanelState, Scenario, Step
from macro_viz.panels.layout import four_panel_layout
from macro_viz.panels.model import N, P, W, Y
from macro_viz.transmission import ASDerivation
from macro_viz.visuals.panels import MARGIN, PANEL_WIDTH, TOP_PAD, linked_panels_canvas
from macro_viz.visuals.transmission._preset import (
    AS_DEMAND_TAIL,
    AS_GAP_SHARE,
    AS_PAD,
    AS_SRAS_DISPLAY_SLOPE,
    AS_SUPPLY_DISPLAY_SLOPE,
    AS_TAIL,
)


def _window(
    states: Sequence[PanelState], pad: Mapping[str, float]
) -> tuple[dict[str, float], dict[str, float]]:
    """Axis lengths and origins that centre A and B and make the lines gentle on screen."""
    low = {v: min(s.values[v] for s in states) for v in (N, W, Y, P)}
    high = {v: max(s.values[v] for s in states) for v in (N, W, Y, P)}
    gap = {v: high[v] - low[v] for v in low}
    if min(gap.values()) <= 0:
        raise ValidationError("the solved states must differ in every variable to draw an AS")
    lengths = {N: gap[N] / AS_GAP_SHARE, Y: gap[Y] / AS_GAP_SHARE}
    # the screen slope of a line is its data slope times the visible width over the visible
    # height times the panel's height over width, which the 45-degree panel fixes
    wide = {v: 1 + MARGIN + pad[v] for v in (N, Y)}
    supply = gap[W] / gap[N]
    lengths[W] = supply * lengths[N] * wide[N] / wide[Y] / AS_SUPPLY_DISPLAY_SLOPE
    lengths[P] = gap[P] / gap[Y] * lengths[Y] / AS_SRAS_DISPLAY_SLOPE
    room = {N: pad[N], Y: pad[Y], W: TOP_PAD, P: TOP_PAD}
    origins = {v: (low[v] + high[v]) / 2 - lengths[v] * (1 + room[v] - MARGIN) / 2 for v in lengths}
    return lengths, origins


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
    pad = {**AS_PAD, **(cast("Mapping[str, float]", options.pop("pad", None) or {}))}
    lengths, origins = _window(scenario.solve(), pad)
    gap_n = lengths[N] * AS_GAP_SHARE
    gap_y = lengths[Y] * AS_GAP_SHARE
    settings: dict[str, object] = {
        "ranges": lengths,
        "origins": origins,
        "tails": {N: AS_TAIL * gap_n, Y: AS_TAIL * gap_y},
        "demand_tail": AS_DEMAND_TAIL * gap_n,
        "pad": pad,
    }
    return linked_panels_canvas(
        scenario,
        four_panel_layout(),
        title=title,
        labels=labels,
        ad=False,
        sras=True,
        shifted_sras=False,
        width=width,
        **{**settings, **options},  # type: ignore[arg-type]
    )
