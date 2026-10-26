"""The curves of the labour market and production panels."""

from __future__ import annotations

from macro_viz.panels.curves._base import _Base
from macro_viz.panels.curves._geometry import (
    _first_index,
    _has_capital,
    _key,
    _linspace,
    price_symbol,
)
from macro_viz.panels.curves._types import VERTICAL, CurveSpec, Subscripted
from macro_viz.panels.layout import PanelSpec
from macro_viz.panels.model import N, P


class _Labor(_Base):
    def labor(self, panel: PanelSpec) -> list[CurveSpec]:
        grid = self._n_grid()
        demand_grid = _linspace(
            self.options.demand_start * self.ranges[N],
            self.options.span[1] * self.ranges[N],
            self.options.samples,
        )
        specs = []
        demand = self._unique(lambda s: _key(s.values[P], s.economy.capital))
        for key, owners in demand:
            state = owners[0]
            price, capital = state.values[P], state.economy.capital
            fields = {
                "price": price_symbol(self.states, price),
                "capital": Subscripted(
                    "capital",
                    _first_index(self.states, _has_capital(capital), "K"),
                ),
            }
            points = [(n, state.economy.labor_demand(n, price)) for n in demand_grid]
            specs.append(
                self._spec(
                    panel,
                    "labor_demand",
                    key,
                    key == demand[0][0],
                    points,
                    "panels.curve.labor_demand",
                    fields,
                    VERTICAL,
                )
            )
        supply = self._unique(
            lambda s: _key(s.economy.expected_price, s.economy.labor_supply.intercept)
        )
        for key, owners in supply:
            state = owners[0]
            pe = state.economy.expected_price
            points = [(n, state.economy.labor_supply_wage(n)) for n in grid]
            fields = {"expected_price": price_symbol(self.states, pe)}
            specs.append(
                self._spec(
                    panel,
                    "labor_supply",
                    key,
                    key == supply[0][0],
                    points,
                    "panels.curve.labor_supply",
                    fields,
                    VERTICAL,
                )
            )
        return specs

    def production(self, panel: PanelSpec) -> list[CurveSpec]:
        grid = self._n_grid()
        groups = self._unique(lambda s: _key(s.economy.capital))
        specs = []
        for key, owners in groups:
            economy = owners[0].economy
            points = [(n, economy.production.output(n, economy.capital)) for n in grid]
            index = owners[0].subscript("K")
            fields = {"capital": Subscripted("capital", index)}
            specs.append(
                self._spec(
                    panel,
                    "production",
                    key,
                    key == groups[0][0],
                    points,
                    "panels.curve.production",
                    fields,
                    VERTICAL,
                )
            )
        return specs
