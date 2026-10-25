"""Typed, renderer-free goods-market models of the Keynesian cross.

Equation conventions (all quantities in one common unit)::

    C = c0 + c1 * YD          consumption; YD = Y - T is disposable income
    Z = c0 + I + G - c1 * T + c1 * Y   demand for goods (planned expenditure)
    Y = Z                     goods-market equilibrium (production equals demand)

``c1`` is the propensity to consume, so ``1 - c1`` is the propensity to save. Investment, government
spending, and taxes are exogenous. The multiplier is ``1 / (1 - c1)``.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from numbers import Real
from typing import Protocol

from macro_viz.direction import Direction
from macro_viz.errors import ValidationError

DEFAULT_TOLERANCE = 1e-9
"""Absolute accuracy of the root found for a curved demand function."""

DEFAULT_ROUNDS = 2
"""How many rounds of the multiplier process an adjustment path lists by default."""


def _finite(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValidationError(f"{name} must be a finite number")
    return float(value)


@dataclass(frozen=True, slots=True)
class ConsumptionFunction:
    """``C = c0 + c1 * YD`` with ``c0 >= 0`` and ``0 < c1 < 1``."""

    autonomous: float
    propensity: float

    def __post_init__(self) -> None:
        autonomous = _finite("autonomous consumption", self.autonomous)
        propensity = _finite("propensity to consume", self.propensity)
        if autonomous < 0:
            raise ValidationError("autonomous consumption must be non-negative")
        if not 0 < propensity < 1:
            raise ValidationError("propensity to consume must lie strictly between 0 and 1")
        object.__setattr__(self, "autonomous", autonomous)
        object.__setattr__(self, "propensity", propensity)

    @property
    def saving_propensity(self) -> float:
        """The propensity to save, ``1 - c1``."""
        return 1.0 - self.propensity

    def consumption(self, disposable_income: float) -> float:
        return self.autonomous + self.propensity * disposable_income

    def saving(self, disposable_income: float) -> float:
        """Disposable income not consumed."""
        return disposable_income - self.consumption(disposable_income)


@dataclass(frozen=True, slots=True)
class GoodsMarketEquilibrium:
    """Output at which production equals demand."""

    output: float
    demand: float
    multiplier: float | None = None


class GoodsMarket(Protocol):
    """What a goods-market figure needs: a demand function and its equilibrium."""

    def demand(self, output: float) -> float: ...

    def equilibrium(self) -> GoodsMarketEquilibrium: ...


@dataclass(frozen=True, slots=True)
class KeynesianCross:
    """Linear goods market: ``Z = c0 + I + G - c1 * T + c1 * Y``."""

    consumption: ConsumptionFunction
    investment: float
    government: float
    taxes: float

    def __post_init__(self) -> None:
        for name in ("investment", "government", "taxes"):
            object.__setattr__(self, name, _finite(name, getattr(self, name)))

    @property
    def autonomous_spending(self) -> float:
        """Demand at zero output, ``c0 + I + G - c1 * T``."""
        return (
            self.consumption.autonomous
            + self.investment
            + self.government
            - self.consumption.propensity * self.taxes
        )

    @property
    def multiplier(self) -> float:
        """``1 / (1 - c1)``."""
        return 1.0 / (1.0 - self.consumption.propensity)

    def demand(self, output: float) -> float:
        return self.autonomous_spending + self.consumption.propensity * output

    def equilibrium(self) -> GoodsMarketEquilibrium:
        output = self.multiplier * self.autonomous_spending
        return GoodsMarketEquilibrium(output, output, self.multiplier)

    def shifted(self, change: float) -> KeynesianCross:
        """The model after autonomous spending changes by ``change`` (through investment)."""
        return KeynesianCross(
            self.consumption,
            self.investment + _finite("autonomous spending change", change),
            self.government,
            self.taxes,
        )


@dataclass(frozen=True, slots=True)
class CurvedDemand:
    """A goods market with a user-supplied increasing demand function.

    ``demand`` maps output to demand; the equilibrium is the root of ``demand(Y) - Y`` found by
    bisection between ``lower`` and ``upper``, which must bracket it.
    """

    demand_function: Callable[[float], float]
    lower: float
    upper: float
    tolerance: float = DEFAULT_TOLERANCE

    def __post_init__(self) -> None:
        lower = _finite("lower bound", self.lower)
        upper = _finite("upper bound", self.upper)
        tolerance = _finite("tolerance", self.tolerance)
        if not lower < upper:
            raise ValidationError("lower bound must be below the upper bound")
        if tolerance <= 0:
            raise ValidationError("tolerance must be positive")
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)
        object.__setattr__(self, "tolerance", tolerance)

    def demand(self, output: float) -> float:
        return float(self.demand_function(output))

    def equilibrium(self) -> GoodsMarketEquilibrium:

        def gap(output: float) -> float:
            return self.demand(output) - output

        low, high = self.lower, self.upper
        if gap(low) < 0 or gap(high) > 0:
            raise ValidationError(
                "the bounds must bracket the equilibrium: demand above output at the lower "
                "bound and below it at the upper bound"
            )
        while high - low > self.tolerance:
            middle = (low + high) / 2
            if gap(middle) >= 0:
                low = middle
            else:
                high = middle
        output = (low + high) / 2
        return GoodsMarketEquilibrium(output, self.demand(output))


@dataclass(frozen=True, slots=True)
class AdjustmentStep:
    """One round of the multiplier process.

    At output ``previous_output`` demand is ``demand``; firms then raise output to ``demand``.
    """

    round: int
    previous_output: float
    demand: float

    @property
    def output(self) -> float:
        """Output at the end of the round, equal to the demand it answers."""
        return self.demand


@dataclass(frozen=True, slots=True)
class AutonomousShift:
    """Baseline and post-change states of a change in autonomous spending."""

    baseline: KeynesianCross
    post: KeynesianCross
    change: float
    direction: Direction
    output_change: float

    @property
    def multiplier(self) -> float:
        return self.baseline.multiplier

    def adjustment_path(self, rounds: int = DEFAULT_ROUNDS) -> tuple[AdjustmentStep, ...]:
        """The rounds of the multiplier process: demand rises first, then production follows.

        Step ``k`` has demand ``Z'(Y_(k-1))`` and then output ``Y_k`` equal to it, with ``Y_0`` the
        baseline output; the path converges to the post-change equilibrium.
        """
        if isinstance(rounds, bool) or not isinstance(rounds, int) or rounds < 1:
            raise ValidationError("rounds must be a positive integer")
        output = self.baseline.equilibrium().output
        steps = []
        for number in range(1, rounds + 1):
            demand = self.post.demand(output)
            steps.append(AdjustmentStep(number, output, demand))
            output = demand
        return tuple(steps)
