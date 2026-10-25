"""Typed, renderer-free Solow growth model (equations given, no optimization).

Equation conventions (per worker, or per effective worker when ``tech_growth`` is positive)::

    y = f(k)                           production per worker; f increasing, concave, f(0) = 0
    k' - k = s f(k) - (delta + gN + gA) k     capital accumulation: saving minus required investment
    steady state k*: s f(k*) = (delta + gN + gA) k*
    c = (1 - s) f(k*)                  steady-state consumption; maximal at the golden rule

``s`` is the saving rate, ``delta`` depreciation, ``gN`` population growth and ``gA`` technological
progress; their sum is the *required* investment rate, the capital that must be added per unit of
capital to keep ``k`` constant. Time is discrete (one step per period).
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, replace
from numbers import Real

from macro_viz.errors import ValidationError

DEFAULT_TOLERANCE = 1e-12
"""Absolute accuracy of the roots found by bisection."""

SEARCH_LIMIT = 80
"""How many times an upper bound may double before a root search gives up."""

DERIVATIVE_STEP = 1e-6
"""Relative step of the numerical derivative of ``f``."""


def _finite(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValidationError(f"{name} must be a finite number")
    return float(value)


@dataclass(frozen=True, slots=True)
class Solow:
    """``k' = k + s f(k) - (delta + gN + gA) k``."""

    production: Callable[[float], float]
    saving: float
    depreciation: float
    population_growth: float = 0.0
    tech_growth: float = 0.0

    def __post_init__(self) -> None:
        saving = _finite("saving rate", self.saving)
        if not 0 < saving < 1:
            raise ValidationError("saving rate must lie strictly between 0 and 1")
        for name in ("depreciation", "population_growth", "tech_growth"):
            value = _finite(name, getattr(self, name))
            if value < 0:
                raise ValidationError(f"{name} must not be negative")
            object.__setattr__(self, name, value)
        if self.required_rate <= 0:
            raise ValidationError("depreciation plus growth rates must be positive")
        object.__setattr__(self, "saving", saving)

    @classmethod
    def cobb_douglas(
        cls,
        alpha: float,
        saving: float,
        depreciation: float,
        population_growth: float = 0.0,
        tech_growth: float = 0.0,
        productivity: float = 1.0,
    ) -> Solow:
        """``f(k) = productivity * k ** alpha`` with ``0 < alpha < 1``."""
        alpha = _finite("alpha", alpha)
        level = _finite("productivity", productivity)
        if not 0 < alpha < 1:
            raise ValidationError("alpha must lie strictly between 0 and 1")
        if level <= 0:
            raise ValidationError("productivity must be positive")
        return cls(lambda k: level * k**alpha, saving, depreciation, population_growth, tech_growth)

    @property
    def required_rate(self) -> float:
        """``delta + gN + gA``: investment per unit of capital that keeps ``k`` constant."""
        return self.depreciation + self.population_growth + self.tech_growth

    def output(self, capital: float) -> float:
        return float(self.production(capital))

    def investment(self, capital: float) -> float:
        """Saving per worker, ``s f(k)``."""
        return self.saving * self.output(capital)

    def required_investment(self, capital: float) -> float:
        return self.required_rate * capital

    def next_capital(self, capital: float) -> float:
        return capital + self.investment(capital) - self.required_investment(capital)

    def steady_state(self) -> float:
        """The positive ``k*`` with ``s f(k) = (delta + gN + gA) k`` (bisection)."""
        low = DERIVATIVE_STEP
        high = 1.0
        for _ in range(SEARCH_LIMIT):
            if self.investment(high) < self.required_investment(high):
                break
            high *= 2
        else:
            raise ValidationError("investment never falls below required investment")
        if self.investment(low) <= self.required_investment(low):
            raise ValidationError("f must rise faster than linearly near zero (f'(0) too small)")
        while high - low > DEFAULT_TOLERANCE * max(1.0, high):
            middle = (low + high) / 2
            if self.investment(middle) > self.required_investment(middle):
                low = middle
            else:
                high = middle
        return (low + high) / 2

    def steady_output(self) -> float:
        return self.output(self.steady_state())

    def steady_consumption(self) -> float:
        return (1 - self.saving) * self.steady_output()

    def golden_rule_capital(self) -> float:
        """The capital with ``f'(k) = delta + gN + gA``, which maximizes steady consumption."""
        f, rate = self.production, self.required_rate

        def slope(k: float) -> float:
            step = DERIVATIVE_STEP * max(1.0, k)
            return float((f(k + step) - f(k - step)) / (2 * step))

        low, high = 2 * DERIVATIVE_STEP, 1.0
        for _ in range(SEARCH_LIMIT):
            if slope(high) < rate:
                break
            high *= 2
        else:
            raise ValidationError("the marginal product never falls to the required rate")
        while high - low > DEFAULT_TOLERANCE * max(1.0, high):
            middle = (low + high) / 2
            if slope(middle) > rate:
                low = middle
            else:
                high = middle
        return (low + high) / 2

    def golden_rule_saving(self) -> float:
        """The saving rate whose steady state is the golden rule: ``required * k_G / f(k_G)``."""
        capital = self.golden_rule_capital()
        return self.required_rate * capital / self.output(capital)

    def consumption_at(self, saving: float) -> float:
        """Steady-state consumption per worker if the saving rate were ``saving``."""
        return replace(self, saving=saving).steady_consumption()

    def with_saving(self, saving: float) -> Solow:
        return replace(self, saving=saving)

    def with_population_growth(self, rate: float) -> Solow:
        return replace(self, population_growth=rate)

    def with_tech_growth(self, rate: float) -> Solow:
        return replace(self, tech_growth=rate)

    def with_production(self, production: Callable[[float], float]) -> Solow:
        return replace(self, production=production)


@dataclass(frozen=True, slots=True)
class SolowPath:
    """Capital and output over time, from a start with a possible change at ``change_period``."""

    capital: tuple[float, ...]
    output: tuple[float, ...]
    change_period: int
    baseline: Solow
    post: Solow

    @property
    def growth_rates(self) -> tuple[float, ...]:
        """Growth rate of output per worker between consecutive periods.

        ``output`` is per effective worker, so the rate adds technological progress:
        ``(1 + g_y)(1 + gA) - 1``. One value fewer than the periods.
        """
        tech = self.post.tech_growth
        return tuple(
            (self.output[t + 1] / self.output[t]) * (1.0 + tech) - 1.0
            for t in range(len(self.output) - 1)
        )

    @property
    def log_output(self) -> tuple[float, ...]:
        """``log`` of output per worker: ``log y_t + t log(1 + gA)`` (the trend of progress)."""
        tech = math.log1p(self.post.tech_growth)
        return tuple(math.log(value) + tech * t for t, value in enumerate(self.output))

    @property
    def periods(self) -> int:
        return len(self.capital)
