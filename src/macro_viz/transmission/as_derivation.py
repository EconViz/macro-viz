"""Renderer-free derivation of the short-run aggregate-supply curve."""

from __future__ import annotations

from dataclasses import dataclass

from macro_viz.panels import MacroEconomy
from macro_viz.transmission._validation import sweep_values


@dataclass(frozen=True, slots=True)
class ASState:
    """Labour, production, and aggregate-supply values at one price level."""

    price: float
    employment: float
    wage: float
    output: float


@dataclass(frozen=True, slots=True)
class ASDerivation:
    """Derive short-run AS from labour demand/supply and the production function."""

    economy: MacroEconomy
    prices: tuple[float, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "prices", sweep_values("price", self.prices, positive=True))

    @property
    def states(self) -> tuple[ASState, ...]:
        states = []
        for price in self.prices:
            employment = self.economy.employment(price)
            states.append(
                ASState(
                    price,
                    employment,
                    self.economy.labor_supply_wage(employment),
                    self.economy.production.output(employment, self.economy.capital),
                )
            )
        return tuple(states)
