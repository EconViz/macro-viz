"""Renderer-free derivation of the LM curve."""

from __future__ import annotations

from dataclasses import dataclass

from macro_viz.money import MoneyMarket
from macro_viz.transmission._validation import sweep_values


@dataclass(frozen=True, slots=True)
class LMState:
    """One money-market equilibrium and its output on the derived LM curve."""

    output: float
    market: MoneyMarket
    rate: float


@dataclass(frozen=True, slots=True)
class LMDerivation:
    """Derive LM by varying real income in the demand for real money balances."""

    money_market: MoneyMarket
    outputs: tuple[float, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "outputs", sweep_values("output", self.outputs, positive=True))

    def market(self, output: float) -> MoneyMarket:
        return self.money_market.with_nominal_income(float(output))

    @property
    def states(self) -> tuple[LMState, ...]:
        return tuple(
            LMState(output, market, market.equilibrium().rate)
            for output in self.outputs
            for market in (self.market(output),)
        )
