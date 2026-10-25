"""Typed, renderer-free IS-LM model with linear relations.

Equation conventions (real quantities; ``R`` is the interest rate)::

    IS:  Y = A - b * R             goods market: ``A`` collects autonomous spending (government
                                   spending, taxes through ``A``, confidence), ``b`` > 0 is the
                                   sensitivity of demand to the interest rate, ``multiplier``
                                   is the Keynesian multiplier applied to ``A``
    LM:  m = d * Y - h * R         money market: real money ``m = M / P`` equals the demand
                                   ``d * Y - h * R`` (``d`` > 0 income, ``h`` >= 0 rate response)

With ``IS: Y = multiplier * (a - b * R)`` the autonomous part ``a`` shifts the curve by
``multiplier * Δa`` at any rate. The price level is fixed, the closure of the short run. ``h`` = 0
makes the LM curve vertical; a very large ``h`` makes it nearly horizontal (a liquidity trap).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from numbers import Real

from macro_viz.errors import ValidationError


def _finite(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValidationError(f"{name} must be a finite number")
    return float(value)


@dataclass(frozen=True, slots=True)
class ISLMEquilibrium:
    """Output and interest rate at which both markets clear."""

    output: float
    rate: float


@dataclass(frozen=True, slots=True)
class ISLM:
    """``IS: Y = multiplier * (autonomous - sensitivity * R)``, ``LM: m = d Y - h R``."""

    autonomous: float
    sensitivity: float
    real_money: float
    income_demand: float
    rate_demand: float
    multiplier: float = 1.0
    zero_bound: bool = False

    def __post_init__(self) -> None:
        for name in ("autonomous", "real_money"):
            object.__setattr__(self, name, _finite(name, getattr(self, name)))
        for name in ("sensitivity", "income_demand", "multiplier"):
            value = _finite(name, getattr(self, name))
            if value <= 0:
                raise ValidationError(f"{name} must be positive")
            object.__setattr__(self, name, value)
        rate_demand = _finite("rate_demand", self.rate_demand)
        if rate_demand < 0:
            raise ValidationError("rate_demand must not be negative")
        object.__setattr__(self, "rate_demand", rate_demand)

    def is_output(self, rate: float) -> float:
        """Output on the IS curve at interest rate ``rate``."""
        return self.multiplier * (self.autonomous - self.sensitivity * rate)

    def lm_rate(self, output: float) -> float:
        """Interest rate on the LM curve at ``output`` (needs ``rate_demand`` above zero)."""
        if self.rate_demand == 0:
            raise ValidationError("the LM curve is vertical: the rate is not a function of output")
        return (self.income_demand * output - self.real_money) / self.rate_demand

    def lm_output(self, rate: float) -> float:
        """Output on the LM curve at interest rate ``rate``."""
        return (self.real_money + self.rate_demand * rate) / self.income_demand

    def equilibrium(self) -> ISLMEquilibrium:
        """Solve ``IS`` and ``LM`` for ``(Y, R)``.

        With ``zero_bound`` the LM curve is flat at ``R = 0`` up to the output ``m / d`` where
        money demand reaches zero interest; an IS curve crossing the flat part gives ``R = 0``.
        """
        m, k, b = self.multiplier, self.income_demand, self.sensitivity
        # Y = m (a - b R) and k Y = real_money + h R
        denominator = k * m * b + self.rate_demand
        rate = (k * m * self.autonomous - self.real_money) / denominator
        if self.zero_bound and rate < 0:
            return ISLMEquilibrium(self.is_output(0.0), 0.0)
        return ISLMEquilibrium(self.is_output(rate), rate)

    def with_zero_bound(self, zero_bound: bool = True) -> ISLM:
        return replace(self, zero_bound=zero_bound)

    def with_autonomous(self, autonomous: float) -> ISLM:
        return replace(self, autonomous=autonomous)

    def with_real_money(self, real_money: float) -> ISLM:
        return replace(self, real_money=real_money)

    def with_rate_demand(self, rate_demand: float) -> ISLM:
        return replace(self, rate_demand=rate_demand)
