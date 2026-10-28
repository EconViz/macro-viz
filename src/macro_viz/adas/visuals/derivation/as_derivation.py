"""Linked-panel derivation of aggregate supply."""

from __future__ import annotations

import string
from collections.abc import Mapping, Sequence
from typing import cast

from mosaickit import CanvasGrid
from mosaickit.layout import centered_view

from macro_viz.adas.as_derivation import ASDerivation
from macro_viz.adas.linked import PanelState, Scenario, Step
from macro_viz.adas.linked.layout import four_panel_layout
from macro_viz.adas.linked.model import N, P, W, Y
from macro_viz.core.errors import ValidationError
from macro_viz.visuals.derivation._preset import (
    AS_DEMAND_TAIL,
    AS_GAP_SHARE,
    AS_PAD,
    AS_PRIMARY_DEMAND_TAIL,
    AS_SRAS_DISPLAY_SLOPE,
    AS_SRAS_TAIL,
    AS_SUPPLY_DISPLAY_SLOPE,
    AS_TAIL,
    POINT_LABEL_ABOVE,
)
from macro_viz.visuals.panels import MARGIN, PANEL_WIDTH, TOP_PAD, linked_panels_canvas


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
    room = {N: pad[N], Y: pad[Y], W: TOP_PAD, P: TOP_PAD}
    views = {
        N: centered_view(
            [(low[N], low[W]), (high[N], high[W])],
            gap_share=AS_GAP_SHARE,
            display_slope=AS_SUPPLY_DISPLAY_SLOPE,
            width=wide[Y],
            height=wide[N],
        ),
        Y: centered_view(
            [(low[Y], low[P]), (high[Y], high[P])],
            gap_share=AS_GAP_SHARE,
            display_slope=AS_SRAS_DISPLAY_SLOPE,
        ),
    }
    spans = {N: views[N].x_span, W: views[N].y_span, Y: views[Y].x_span, P: views[Y].y_span}
    # With a genuine zero on the output axis, keep the two solved outputs visually centred by
    # lengthening the range instead of translating the production function away from its origin.
    old_y_span = spans[Y]
    spans[Y] = (low[Y] + high[Y]) / (1 + pad[Y] - MARGIN)
    spans[P] *= spans[Y] / old_y_span
    starts = {
        N: views[N].x_origin,
        W: views[N].y_origin,
        Y: views[Y].x_origin,
        P: (low[P] + high[P] - spans[P]) / 2,
    }
    # centre the pair of states inside the drawn area, which is MARGIN short of the span
    lengths = spans
    origins = {v: starts[v] - spans[v] * (room[v] - MARGIN) / 2 for v in spans}
    # Employment and output keep their economic origin so the production function is the
    # model's own concave F(N, K), beginning at (0, 0), rather than a translated segment.
    origins[N] = 0.0
    origins[Y] = 0.0
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
        "tails": {N: AS_TAIL * gap_n, Y: AS_SRAS_TAIL * gap_y},
        "demand_tail": AS_DEMAND_TAIL * gap_n,
        "primary_demand_tail": AS_PRIMARY_DEMAND_TAIL * gap_n,
        "pad": pad,
        "point_label_offset": POINT_LABEL_ABOVE,
        "production_from_origin": True,
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
