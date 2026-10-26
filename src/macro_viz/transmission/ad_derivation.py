"""Renderer-free derivation of the aggregate-demand curve."""

from __future__ import annotations

from dataclasses import dataclass

from macro_viz.errors import ValidationError
from macro_viz.islm import ISLM
from macro_viz.transmission._validation import positive_number, sweep_values


@dataclass(frozen=True, slots=True)
class ADState:
    """An IS-LM equilibrium at one price level and therefore one point on AD."""

    price: float
    model: ISLM
    output: float
    rate: float


@dataclass(frozen=True, slots=True)
class ADDerivation:
    """Derive AD by varying ``p`` while nominal money ``M`` remains fixed."""

    islm: ISLM
    nominal_money: float
    prices: tuple[float, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "nominal_money",
            positive_number("nominal money", self.nominal_money),
        )
        object.__setattr__(self, "prices", sweep_values("price", self.prices, positive=True))

    def model(self, price: float) -> ISLM:
        if price <= 0:
            raise ValidationError("price must be positive")
        return self.islm.with_real_money(self.nominal_money / float(price))

    @property
    def states(self) -> tuple[ADState, ...]:
        return tuple(
            ADState(price, model, equilibrium.output, equilibrium.rate)
            for price in self.prices
            for model in (self.model(price),)
            for equilibrium in (model.equilibrium(),)
        )
