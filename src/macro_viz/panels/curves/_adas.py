"""The curves of the AD-AS panel."""

from __future__ import annotations

from collections.abc import Callable

from macro_viz.errors import ValidationError
from macro_viz.panels.curves._base import _Base, _price_for_output
from macro_viz.panels.curves._geometry import _key, price_symbol
from macro_viz.panels.curves._types import HORIZONTAL, CurveSpec, Mode, Point, Subscripted
from macro_viz.panels.layout import PanelSpec
from macro_viz.panels.model import P, Y
from macro_viz.panels.scenario import PanelState


class _Adas(_Base):
    def adas(self, panel: PanelSpec) -> list[CurveSpec]:
        o = self.options
        specs: list[CurveSpec] = []
        schematic = o.mode is Mode.SCHEMATIC
        top = o.headroom * self.ranges[P]
        if o.sras:
            groups = self._unique(lambda s: _key(s.economy.capital, s.economy.expected_price))
            if not o.shifted_sras:
                groups = groups[:1]
            curves: dict[tuple[float, ...], list[Point]] = {}
            if schematic:
                economies = {key: owners[0].economy for key, owners in groups}
                anchors = {
                    key: [(s.values[Y], s.values[P]) for s in owners] for key, owners in groups
                }

                def inverse(key: tuple[float, ...]) -> Callable[[float], float]:
                    economy = economies[key]
                    return lambda y: _price_for_output(economy, y, top)

                curves = self._straight(anchors, inverse)
            else:
                for key, owners in groups:
                    economy = owners[0].economy
                    curves[key] = [(economy.output(p), p) for p in self._price_grid(owners[0])]
            for key, owners in groups:
                state = owners[0]
                fields = {
                    "capital": Subscripted("capital", state.subscript("K")),
                    "expected_price": price_symbol(self.states, state.economy.expected_price),
                }
                specs.append(
                    self._spec(
                        panel,
                        "sras",
                        key,
                        key == groups[0][0],
                        curves[key],
                        "panels.curve.sras",
                        fields,
                        HORIZONTAL,
                    )
                )
        if o.lras:
            groups = self._unique(lambda s: _key(s.economy.natural_output))
            for key, owners in groups:
                y = owners[0].economy.natural_output
                specs.append(
                    self._spec(
                        panel,
                        "lras",
                        key,
                        key == groups[0][0],
                        [(y, 0.0), (y, top / o.headroom)],
                        "panels.curve.lras",
                        {},
                        HORIZONTAL,
                    )
                )
        if o.ad:
            specs += self._demand(panel)
        return specs

    def _demand(self, panel: PanelSpec) -> list[CurveSpec]:
        clearing = [s for s in self.states if s.clearing]
        if not clearing:
            return []
        sketch = self.scenario.sketch is not None
        if sketch:
            groups: list[tuple[tuple[float, ...], list[PanelState]]] = [((), clearing)]
        else:
            groups = [
                (key, owners)
                for key, owners in self._unique(
                    lambda s: (
                        _key(s.economy.islm.money, s.economy.islm.expenditure)
                        if s.clearing and s.economy.islm is not None
                        else None
                    )
                )
            ]
        specs = []
        curves: dict[tuple[float, ...], list[Point]] = {}
        if self.options.mode is Mode.SCHEMATIC or sketch:
            anchors = {key: [(s.values[Y], s.values[P]) for s in owners] for key, owners in groups}
            islms = {key: owners[0].economy.islm for key, owners in groups}

            def inverse(key: tuple[float, ...]) -> Callable[[float], float]:
                islm = islms[key]
                if islm is None:
                    raise ValidationError("a single point does not fix a sketched AD")
                return lambda y: islm.demand_price(y)

            curves = self._straight(anchors, inverse)
        else:
            for key, owners in groups:
                islm = owners[0].economy.islm
                assert islm is not None
                grid = self._price_grid(owners[0])
                curves[key] = [(islm.demand_output(p), p) for p in reversed(grid)]
        for key, owners in groups:
            main = key == groups[0][0]
            index = owners[0].subscript(P)
            fields = {"index": index}
            specs.append(
                self._spec(
                    panel,
                    "ad",
                    key,
                    main,
                    curves[key],
                    "panels.curve.ad" if main else "panels.curve.ad_shifted",
                    fields,
                    HORIZONTAL,
                )
            )
        return specs
