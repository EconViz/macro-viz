"""The curve builder of every panel kind and its entry points."""

from __future__ import annotations

import math
from collections.abc import Sequence

from macro_viz.adas.linked.curves._adas import _Adas
from macro_viz.adas.linked.curves._islm import _Islm
from macro_viz.adas.linked.curves._labor import _Labor
from macro_viz.adas.linked.curves._types import CurveOptions, CurveSpec
from macro_viz.adas.linked.curves.ranges import Ranges
from macro_viz.adas.linked.layout import ADAS, ISLM, LABOR, PRODUCTION, PanelSpec
from macro_viz.adas.linked.scenario import PanelState, Scenario


class _Builder(_Labor, _Adas, _Islm):
    def specs(self, panel: PanelSpec) -> list[CurveSpec]:
        build = {
            LABOR: self.labor,
            PRODUCTION: self.production,
            ADAS: self.adas,
            ISLM: self.islm,
        }.get(panel.kind)
        return build(panel) if build is not None else []


def curve_specs(
    panel: PanelSpec,
    scenario: Scenario,
    states: Sequence[PanelState],
    ranges: Ranges,
    options: CurveOptions,
) -> list[CurveSpec]:
    """Every curve of ``panel`` for the solved ``states``."""
    return _Builder(scenario, states, ranges, options).specs(panel)


def sample_rate(curve: CurveSpec) -> float:
    """The length of the curve's polyline (used to place arrows along it)."""
    return sum(math.dist(a, b) for a, b in zip(curve.points, curve.points[1:], strict=False))
