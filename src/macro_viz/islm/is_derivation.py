"""Renderer-free derivation of the IS curve."""

from __future__ import annotations

from dataclasses import dataclass, replace

from macro_viz.core.validation import positive_number, sweep_values
from macro_viz.keynesian import KeynesianCross


@dataclass(frozen=True, slots=True)
class ISState:
    """One goods-market equilibrium and its interest rate on the derived IS curve."""

    rate: float
    market: KeynesianCross
    output: float
    investment: float


@dataclass(frozen=True, slots=True)
class ISDerivation:
    """Derive IS by varying ``r`` in ``I(r) = I(0) - sensitivity * r``."""

    goods_at_zero_rate: KeynesianCross
    investment_sensitivity: float
    rates: tuple[float, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "investment_sensitivity",
            positive_number("investment sensitivity", self.investment_sensitivity),
        )
        object.__setattr__(self, "rates", sweep_values("rate", self.rates))

    def market(self, rate: float) -> KeynesianCross:
        return replace(
            self.goods_at_zero_rate,
            investment=self.goods_at_zero_rate.investment
            - self.investment_sensitivity * float(rate),
        )

    @property
    def states(self) -> tuple[ISState, ...]:
        return tuple(
            ISState(rate, market, market.equilibrium().output, market.investment)
            for rate in self.rates
            for market in (self.market(rate),)
        )
