"""Typed, renderer-free money-market models.

Equation conventions (nominal quantities in one common unit)::

    Md = $Y * L(i)     money demand: nominal income times liquidity preference L(i)
    Ms = M             money supply, chosen by the central bank, independent of i
    Md = Ms            money-market equilibrium, which determines the interest rate i

``L`` is positive and strictly decreasing: a higher interest rate lowers the demand for money.
The interest rate is the rate on bonds and is not negative here.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from numbers import Real

from macro_viz.direction import Direction
from macro_viz.errors import ValidationError

DEFAULT_TOLERANCE = 1e-10
"""Absolute accuracy of the interest rate found by bisection."""


def _finite(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValidationError(f"{name} must be a finite number")
    return float(value)


class Curve(str, Enum):
    """Which curve of the money market moves."""

    DEMAND = "demand"
    SUPPLY = "supply"


@dataclass(frozen=True, slots=True)
class MoneyDemand:
    """``Md = nominal_income * L(i)`` with ``L`` positive and decreasing in the rate.

    ``liquidity`` is ``L``; ``rate_max`` is the highest interest rate the model considers (the
    top of the vertical axis, and the upper bound of the search for the equilibrium rate). With
    ``zero_bound`` the interest rate cannot fall below zero: when the money supply exceeds the
    demand at a zero rate, people hold the extra money at no cost (a liquidity trap) and the
    rate stays at zero.
    """

    nominal_income: float
    liquidity: Callable[[float], float]
    rate_max: float
    zero_bound: bool = False

    def __post_init__(self) -> None:
        income = _finite("nominal income", self.nominal_income)
        rate_max = _finite("rate_max", self.rate_max)
        if income <= 0:
            raise ValidationError("nominal income must be positive")
        if rate_max <= 0:
            raise ValidationError("rate_max must be positive")
        object.__setattr__(self, "nominal_income", income)
        object.__setattr__(self, "rate_max", rate_max)
        if not self.liquidity(0.0) > self.liquidity(rate_max) > 0:
            raise ValidationError(
                "liquidity must be positive and lower at rate_max than at a zero rate"
            )

    def quantity(self, rate: float) -> float:
        """Money demanded at interest rate ``rate``."""
        return self.nominal_income * float(self.liquidity(rate))

    def rate(self, money: float, tolerance: float = DEFAULT_TOLERANCE) -> float:
        """The interest rate at which the quantity demanded equals ``money`` (bisection)."""
        low, high = 0.0, self.rate_max
        if self.zero_bound and money >= self.quantity(0.0):
            return 0.0
        if not self.quantity(high) <= money <= self.quantity(low):
            raise ValidationError(
                "money supply must lie between the demand at the highest and at a zero rate"
            )
        while high - low > tolerance:
            middle = (low + high) / 2
            if self.quantity(middle) > money:
                low = middle
            else:
                high = middle
        return (low + high) / 2

    def with_nominal_income(self, nominal_income: float) -> MoneyDemand:
        return MoneyDemand(nominal_income, self.liquidity, self.rate_max, self.zero_bound)


@dataclass(frozen=True, slots=True)
class MoneyMarketEquilibrium:
    """The interest rate and quantity of money at which demand equals supply."""

    rate: float
    money: float


@dataclass(frozen=True, slots=True)
class MoneyMarket:
    """Money demand and a fixed money supply."""

    demand: MoneyDemand
    supply: float

    def __post_init__(self) -> None:
        supply = _finite("money supply", self.supply)
        if supply <= 0:
            raise ValidationError("money supply must be positive")
        object.__setattr__(self, "supply", supply)

    def equilibrium(self) -> MoneyMarketEquilibrium:
        """``i`` solving ``$Y L(i) = M``."""
        return MoneyMarketEquilibrium(self.demand.rate(self.supply), self.supply)

    def with_nominal_income(self, nominal_income: float) -> MoneyMarket:
        return MoneyMarket(self.demand.with_nominal_income(nominal_income), self.supply)

    def with_supply(self, supply: float) -> MoneyMarket:
        return MoneyMarket(self.demand, supply)


@dataclass(frozen=True, slots=True)
class MoneyMarketShift:
    """Baseline and post-change money markets with the direction of every change."""

    baseline: MoneyMarket
    post: MoneyMarket
    curve: Curve
    rate_direction: Direction
    money_direction: Direction

    @property
    def rate_change(self) -> float:
        return self.post.equilibrium().rate - self.baseline.equilibrium().rate

    @property
    def money_change(self) -> float:
        return self.post.supply - self.baseline.supply


@dataclass(frozen=True, slots=True)
class MoneyMultiplier:
    """Central-bank money behind a stock of money: ``H = [c + theta (1 - c)] M``.

    ``currency_ratio`` ``c`` is currency over money held by the public and ``reserve_ratio``
    ``theta`` is reserves over deposits; the money multiplier is ``1 / (c + theta (1 - c))``.
    """

    currency_ratio: float
    reserve_ratio: float

    def __post_init__(self) -> None:
        for name in ("currency_ratio", "reserve_ratio"):
            value = _finite(name, getattr(self, name))
            if not 0 <= value <= 1:
                raise ValidationError(f"{name} must lie between 0 and 1")
            object.__setattr__(self, name, value)
        if self.base_ratio <= 0:
            raise ValidationError("currency and reserve ratios cannot both be zero")

    @property
    def base_ratio(self) -> float:
        """Central-bank money per unit of money, ``c + theta (1 - c)``."""
        return self.currency_ratio + self.reserve_ratio * (1.0 - self.currency_ratio)

    @property
    def multiplier(self) -> float:
        """Money per unit of central-bank money, ``1 / (c + theta (1 - c))``."""
        return 1.0 / self.base_ratio

    def base_demand(self, demand: MoneyDemand) -> MoneyDemand:
        """The demand for central-bank money ``H^d = base_ratio * $Y L(R)``."""
        return MoneyDemand(
            demand.nominal_income * self.base_ratio,
            demand.liquidity,
            demand.rate_max,
            demand.zero_bound,
        )

    def market(self, market: MoneyMarket) -> MoneyMarket:
        """The market for central-bank money: demand ``H^d`` against supply ``M / multiplier``."""
        return MoneyMarket(self.base_demand(market.demand), market.supply / self.multiplier)
