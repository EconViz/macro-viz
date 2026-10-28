"""The curves of the IS-LM panel."""

from __future__ import annotations

from collections.abc import Sequence

from macro_viz.adas.linked.curves._base import _Base
from macro_viz.adas.linked.curves._geometry import _key, _line, price_symbol
from macro_viz.adas.linked.curves._types import HORIZONTAL, CurveSpec, Point, Subscripted
from macro_viz.adas.linked.layout import PanelSpec
from macro_viz.adas.linked.model import P, R, Y
from macro_viz.adas.linked.scenario import PanelState


class _Islm(_Base):
    def islm(self, panel: PanelSpec) -> list[CurveSpec]:
        on = [s for s in self.states if R in s.values]
        if not on:
            return []
        reach = self.options.reach * self.ranges[Y]
        lo = min(s.values[Y] for s in on) - reach
        hi = max(s.values[Y] for s in on) + reach
        sketch = self.scenario.sketch
        specs: list[CurveSpec] = []
        if sketch is not None:
            origin = on[0]
            is_line = _line((origin.values[Y], origin.values[R]), sketch.is_slope, lo, hi)
            specs.append(
                self._spec(panel, "is", (), True, is_line, "panels.curve.is", {}, HORIZONTAL)
            )
            for state in on:
                line = _line(
                    (state.values[Y], state.values[R]),
                    sketch.lm_slope,
                    state.values[Y] - reach,
                    state.values[Y] + reach,
                )
                specs.append(self._lm(panel, state, line, state is on[0]))
            return specs
        groups = self._unique(
            lambda s: _key(s.economy.islm.expenditure) if R in s.values and s.economy.islm else None
        )
        for key, owners in groups:
            islm = owners[0].economy.islm
            assert islm is not None
            line = [(y, islm.is_rate(y)) for y in (lo, hi)]
            main = key == groups[0][0]
            specs.append(
                self._spec(
                    panel,
                    "is",
                    key,
                    main,
                    line,
                    "panels.curve.is" if main else "panels.curve.is_shifted",
                    {"index": owners[0].index},
                    HORIZONTAL,
                )
            )
        lms = self._unique(
            lambda s: (
                _key(s.economy.islm.money, s.values[P])
                if R in s.values and s.economy.islm
                else None
            )
        )
        for key, owners in lms:
            state = owners[0]
            islm = state.economy.islm
            assert islm is not None
            price = state.values[P]
            line = [
                (y, islm.lm_rate(y, price))
                for y in (state.values[Y] - reach, state.values[Y] + reach)
            ]
            specs.append(self._lm(panel, state, line, key == lms[0][0]))
        return specs

    def _lm(
        self, panel: PanelSpec, state: PanelState, line: Sequence[Point], main: bool
    ) -> CurveSpec:
        fields = {
            "money": Subscripted("money", self.base.subscript(P)),
            "price": price_symbol(self.states, state.values[P]),
        }
        return self._spec(
            panel, "lm", _key(state.values[P]), main, line, "panels.curve.lm", fields, HORIZONTAL
        )
