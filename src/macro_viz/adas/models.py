"""Typed, renderer-free aggregate-supply and aggregate-demand models.

Equation conventions (the price level ``P`` and output ``Y`` in one common unit)::

    P  = scale * Pe * h(Y)          aggregate supply (AS): upward sloping, h(Yn) = 1
    Y  = A + k * M / P              aggregate demand (AD): downward sloping in (Y, P) space

``Pe`` is the expected price level, ``Yn`` natural output (where the price level equals its
expected value), ``h`` the response of the price level to output (given), and ``scale`` a cost
factor that a supply shock changes (productivity, for instance). In ``AD``, ``A`` collects what
shifts demand at any price level (government spending, taxes, confidence), ``M`` is nominal
money, and ``k`` the demand multiplier of real money balances. Only the equations are given; the
closure is the short run in which ``Pe`` is fixed. Natural output is an input here.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import Enum
from numbers import Real

from macro_viz.errors import ValidationError

DEFAULT_TOLERANCE = 1e-10
"""Absolute accuracy of the output found by bisection."""

SEARCH_LIMIT = 60
"""How many times the upper bound of the equilibrium search may double before giving up."""


def _finite(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValidationError(f"{name} must be a finite number")
    return float(value)


def _positive(name: str, value: float) -> float:
    value = _finite(name, value)
    if value <= 0:
        raise ValidationError(f"{name} must be positive")
    return value


class Gap(str, Enum):
    """Where equilibrium output stands relative to natural output."""

    RECESSIONARY = "recessionary"
    INFLATIONARY = "inflationary"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class AggregateSupply:
    """``P = scale * Pe * h(Y)``; ``response`` is ``h``, increasing with ``h(Yn) = 1``."""

    expected_price: float
    natural_output: float
    response: Callable[[float], float]
    scale: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "expected_price", _positive("expected price", self.expected_price))
        object.__setattr__(self, "natural_output", _positive("natural output", self.natural_output))
        object.__setattr__(self, "scale", _positive("scale", self.scale))
        if abs(self.response(self.natural_output) - 1.0) > 1e-9:
            raise ValidationError("the price response must equal one at natural output")
        if self.response(0.0) < 0:
            raise ValidationError("the price response must not be negative at zero output")

    @classmethod
    def linear(cls, expected_price: float, natural_output: float, slope: float) -> AggregateSupply:
        """``h(Y) = 1 + slope * (Y / Yn - 1)`` with ``0 < slope < 1``, so prices stay positive."""
        slope = _finite("slope", slope)
        natural = _positive("natural output", natural_output)
        if not 0 < slope < 1:
            raise ValidationError("slope must lie strictly between 0 and 1")
        return cls(expected_price, natural, lambda y: 1.0 + slope * (y / natural - 1.0))

    def price(self, output: float) -> float:
        """The price level firms set at ``output``."""
        return self.scale * self.expected_price * float(self.response(output))

    @property
    def effective_natural_output(self) -> float:
        """Output at which the price level equals its expected value: ``scale * h(Y) = 1``.

        It equals ``natural_output`` while ``scale`` is one; a cost shock (``scale`` above one)
        lowers it and a productivity gain (``scale`` below one) raises it.
        """
        if self.scale == 1.0:
            return self.natural_output
        low, high = 0.0, self.natural_output
        for _ in range(SEARCH_LIMIT):
            if self.scale * float(self.response(high)) >= 1.0:
                break
            high *= 2
        else:
            raise ValidationError("the price response never reaches the expected price level")
        while high - low > DEFAULT_TOLERANCE:
            middle = (low + high) / 2
            if self.scale * float(self.response(middle)) >= 1.0:
                high = middle
            else:
                low = middle
        return (low + high) / 2

    def with_expected_price(self, expected_price: float) -> AggregateSupply:
        return replace(self, expected_price=expected_price)

    def with_scale(self, scale: float) -> AggregateSupply:
        return replace(self, scale=scale)


@dataclass(frozen=True, slots=True)
class AggregateDemand:
    """``Y = autonomous + multiplier * money / P`` for ``P > 0``."""

    autonomous: float
    money: float
    multiplier: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "autonomous", _finite("autonomous demand", self.autonomous))
        object.__setattr__(self, "money", _positive("nominal money", self.money))
        object.__setattr__(self, "multiplier", _positive("multiplier", self.multiplier))

    def output(self, price: float) -> float:
        """Output demanded at price level ``price``."""
        if price <= 0:
            raise ValidationError("the price level must be positive")
        return self.autonomous + self.multiplier * self.money / price

    def price(self, output: float) -> float:
        """The price level at which ``output`` is demanded (``output`` above ``autonomous``)."""
        if output <= self.autonomous:
            raise ValidationError("demand exceeds its autonomous part only at a finite price")
        return self.multiplier * self.money / (output - self.autonomous)

    def with_autonomous(self, autonomous: float) -> AggregateDemand:
        return replace(self, autonomous=autonomous)

    def with_money(self, money: float) -> AggregateDemand:
        return replace(self, money=money)


@dataclass(frozen=True, slots=True)
class ASADEquilibrium:
    """Short-run equilibrium: the crossing of AS and AD, and where it stands against ``Yn``."""

    output: float
    price: float
    natural_output: float
    expected_price: float
    gap: Gap

    @property
    def output_gap(self) -> float:
        """``Y - Yn``: negative in a recession, positive in a boom."""
        return self.output - self.natural_output


@dataclass(frozen=True, slots=True)
class ASADModel:
    """An aggregate supply and an aggregate demand curve."""

    supply: AggregateSupply
    demand: AggregateDemand
    tolerance: float = DEFAULT_TOLERANCE

    def equilibrium(self) -> ASADEquilibrium:
        """The output ``Y`` at which ``AS`` and ``AD`` give the same price level."""
        low = self.demand.autonomous + self.tolerance

        def gap(output: float) -> float:
            return self.supply.price(output) - self.demand.price(output)

        high = max(2 * low, self.supply.natural_output)
        for _ in range(SEARCH_LIMIT):
            if gap(high) > 0:
                break
            high *= 2
        else:
            raise ValidationError("aggregate supply and demand do not cross")
        while high - low > self.tolerance:
            middle = (low + high) / 2
            if gap(middle) > 0:
                high = middle
            else:
                low = middle
        output = (low + high) / 2
        natural = self.supply.effective_natural_output
        spread = self.tolerance * 1e3 + 1e-9 * natural
        if output < natural - spread:
            kind = Gap.RECESSIONARY
        elif output > natural + spread:
            kind = Gap.INFLATIONARY
        else:
            kind = Gap.NONE
        return ASADEquilibrium(
            output=output,
            price=self.supply.price(output),
            natural_output=natural,
            expected_price=self.supply.expected_price,
            gap=kind,
        )

    def with_supply(self, supply: AggregateSupply) -> ASADModel:
        return replace(self, supply=supply)

    def with_demand(self, demand: AggregateDemand) -> ASADModel:
        return replace(self, demand=demand)


def employment(output: float, productivity: float) -> float:
    """Employment ``N = Y / A`` for output ``output`` and labour productivity ``A``."""
    return _finite("output", output) / _positive("productivity", productivity)
