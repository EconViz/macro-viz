"""Typed, renderer-free blocks of the linked-panel macro diagram, and the shocks that move them.

Four blocks share one economy. Every symbol below is a field of a typed object; no number is
written into a formula.

Labour market (employment ``N``, nominal wage ``W``, price level ``p``)::

    W = p * f(N, K)             labour demand, f = marginal product of labour, decreasing in N
    W = pe * h(N)               labour supply, h increasing; pe is the expected price level

Production function (output ``Y``, capital ``K``)::

    Y = F(N, K) = K**theta * (a*N - b*N**2 / 2)        concave in N; f = K**theta * (a - b*N)

Aggregate supply: for a price level ``p`` the labour market gives ``N(p)`` and ``Y = F(N(p), K)``.
With ``pe`` fixed this is the short-run aggregate supply (SRAS); when ``pe = p`` the price level
cancels and output is the natural level ``Yn`` whatever ``p`` is (LRAS, vertical).

IS-LM (interest rate ``R``, money ``M``)::

    IS:  Y = X - e*R                 X: autonomous expenditure, e: interest sensitivity
    LM:  M / p = k*Y - h_r*R         real money supply equals real money demand

Eliminating ``R`` gives aggregate demand ``Y = (X + (e / h_r) * M / p) / (1 + e*k / h_r)``,
decreasing in ``p``. The 45-degree line carries ``Y`` from one panel to another and adds nothing.

The goods market clears at the price level where aggregate demand equals aggregate supply, so
``Y`` of the production function, of AD-AS and of IS-LM is one number at such a point.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from numbers import Real
from typing import TYPE_CHECKING

from macro_viz.errors import ValidationError
from macro_viz.panels.solve import bisect, bisect_above

if TYPE_CHECKING:
    from macro_viz.panels.movement import Curve, EconomicCurve

N, W, Y, P, R = "N", "W", "Y", "p", "R"
"""Ids of the variables a panel can show; the text drawn for each is in the locale table."""


def _positive(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValidationError(f"{name} must be a finite number")
    if value <= 0:
        raise ValidationError(f"{name} must be positive")
    return float(value)


def _finite(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValidationError(f"{name} must be a finite number")
    return float(value)


@dataclass(frozen=True, slots=True)
class LinearFunction:
    """``intercept + slope * x``; the labour supply schedule ``h`` of the labour market."""

    intercept: float
    slope: float

    def __post_init__(self) -> None:
        _positive("intercept", self.intercept)
        if _finite("slope", self.slope) < 0:
            raise ValidationError("slope must not be negative")

    def __call__(self, x: float) -> float:
        return self.intercept + self.slope * x


@dataclass(frozen=True, slots=True)
class QuadraticProduction:
    """``Y = F(N, K) = K**elasticity * (productivity*N - curvature*N**2 / 2)``, concave in ``N``."""

    productivity: float
    curvature: float
    elasticity: float

    def __post_init__(self) -> None:
        for name in ("productivity", "curvature", "elasticity"):
            _positive(name, getattr(self, name))

    @property
    def employment_limit(self) -> float:
        """The employment at which the marginal product reaches zero."""
        return self.productivity / self.curvature

    def scale(self, capital: float) -> float:
        return float(capital**self.elasticity)

    def output(self, employment: float, capital: float) -> float:
        n = employment
        return self.scale(capital) * (self.productivity * n - self.curvature * n * n / 2)

    def marginal_product(self, employment: float, capital: float) -> float:
        return self.scale(capital) * (self.productivity - self.curvature * employment)


@dataclass(frozen=True, slots=True)
class IsLm:
    """``IS: Y = X - e R`` and ``LM: M / p = k Y - h R`` (see the module docstring)."""

    expenditure: float
    money: float
    interest_sensitivity: float
    income_demand: float
    interest_demand: float

    def __post_init__(self) -> None:
        _finite("expenditure", self.expenditure)
        for name in ("money", "interest_sensitivity", "income_demand", "interest_demand"):
            _positive(name, getattr(self, name))

    @property
    def _denominator(self) -> float:
        return 1 + self.interest_sensitivity * self.income_demand / self.interest_demand

    def real_money(self, price: float) -> float:
        return self.money / price

    def is_rate(self, output: float) -> float:
        return (self.expenditure - output) / self.interest_sensitivity

    def lm_rate(self, output: float, price: float) -> float:
        return (self.income_demand * output - self.real_money(price)) / self.interest_demand

    def demand_output(self, price: float) -> float:
        """Aggregate demand: the output at which IS and LM cross for price level ``price``."""
        ratio = self.interest_sensitivity / self.interest_demand
        return (self.expenditure + ratio * self.real_money(price)) / self._denominator

    def demand_price(self, output: float) -> float:
        """The inverse of aggregate demand: the price level that makes AD equal ``output``."""
        ratio = self.interest_sensitivity / self.interest_demand
        room = output * self._denominator - self.expenditure
        if room <= 0:
            raise ValidationError("no price level makes aggregate demand this large")
        return ratio * self.money / room

    def equilibrium_rate(self, price: float) -> float:
        return self.is_rate(self.demand_output(price))

    def calibrated(self, output: float, price: float, rate: float) -> IsLm:
        """This IS-LM with ``X`` and ``M`` chosen so that IS and LM cross at ``(output, rate)``.

        ``price`` is the price level at which they cross. ``X = Y + e R`` and
        ``M = p (k Y - h_r R)``; the sensitivities are kept.
        """
        spending = output + self.interest_sensitivity * rate
        money = price * (self.income_demand * output - self.interest_demand * rate)
        if money <= 0:
            raise ValidationError("the rate is too high for a positive money supply")
        return replace(self, expenditure=spending, money=money)


@dataclass(frozen=True, slots=True)
class Shock:
    """A change of parameters; a field left ``None`` keeps the economy's value."""

    capital: float | None = None
    expected_price: float | None = None
    money: float | None = None
    expenditure: float | None = None
    labor_supply_shift: float | None = None
    """Added to the intercept of labour supply (an increase in labour supply is negative)."""

    def apply(self, economy: MacroEconomy) -> MacroEconomy:
        changed = economy
        if self.capital is not None:
            changed = replace(changed, capital=_positive("capital", self.capital))
        if self.expected_price is not None:
            changed = replace(
                changed, expected_price=_positive("expected_price", self.expected_price)
            )
        if self.labor_supply_shift is not None:
            supply = changed.labor_supply
            changed = replace(
                changed,
                labor_supply=LinearFunction(
                    supply.intercept + self.labor_supply_shift, supply.slope
                ),
            )
        if self.money is not None or self.expenditure is not None:
            if changed.islm is None:
                raise ValidationError("money and expenditure shocks need an IS-LM block")
            islm = changed.islm
            changed = replace(
                changed,
                islm=replace(
                    islm,
                    money=islm.money if self.money is None else self.money,
                    expenditure=(
                        islm.expenditure if self.expenditure is None else self.expenditure
                    ),
                ),
            )
        return changed


@dataclass(frozen=True, slots=True)
class MacroEconomy:
    """Labour market, production function and (optionally) IS-LM with their parameters."""

    production: QuadraticProduction
    labor_supply: LinearFunction
    capital: float
    expected_price: float
    islm: IsLm | None = None

    def __post_init__(self) -> None:
        _positive("capital", self.capital)
        _positive("expected_price", self.expected_price)

    def labor_demand(self, employment: float, price: float) -> float:
        """The nominal wage firms pay at ``employment``: ``p * f(N, K)``."""
        return price * self.production.marginal_product(employment, self.capital)

    def labor_supply_wage(self, employment: float, expected_price: float | None = None) -> float:
        """The nominal wage workers ask at ``employment``: ``pe * h(N)``."""
        pe = self.expected_price if expected_price is None else expected_price
        return pe * self.labor_supply(employment)

    def employment(self, price: float, expected_price: float | None = None) -> float:
        """Employment where labour demand equals labour supply; zero if supply asks too much."""
        pe = self.expected_price if expected_price is None else expected_price

        def excess(n: float) -> float:
            return self.labor_demand(n, price) - self.labor_supply_wage(n, pe)

        limit = self.production.employment_limit
        if excess(0.0) <= 0:
            return 0.0
        return bisect(excess, 0.0, limit)

    def wage(self, price: float) -> float:
        return self.labor_supply_wage(self.employment(price))

    def output(self, price: float, expected_price: float | None = None) -> float:
        """Short-run aggregate supply: the output firms offer at price level ``price``."""
        n = self.employment(price, expected_price)
        return self.production.output(n, self.capital)

    @property
    def natural_employment(self) -> float:
        """Employment when the expected price is right (``pe = p``, which cancels the price)."""

        def excess(n: float) -> float:
            return self.production.marginal_product(n, self.capital) - self.labor_supply(n)

        return bisect(excess, 0.0, self.production.employment_limit)

    @property
    def natural_output(self) -> float:
        """Long-run aggregate supply: output at natural employment, whatever the price level."""
        return self.production.output(self.natural_employment, self.capital)

    def price_floor(self) -> float:
        """The price level below which no one is employed."""
        a = self.production.marginal_product(0.0, self.capital)
        return self.expected_price * self.labor_supply(0.0) / a

    def demand_output(self, price: float) -> float:
        if self.islm is None:
            raise ValidationError("this economy has no IS-LM block")
        return self.islm.demand_output(price)

    def clearing_price(self) -> float:
        """The price level at which aggregate demand equals short-run aggregate supply."""
        floor = self.price_floor()

        def excess_demand(price: float) -> float:
            return self.demand_output(price) - self.output(price)

        return bisect_above(excess_demand, floor, 2 * floor)

    def calibrated(self, rate: float, price: float | None = None) -> MacroEconomy:
        """This economy with IS and LM placed to cross at the output firms offer at ``price``.

        ``price`` defaults to the expected price level, the starting point of every scenario;
        ``rate`` is the interest rate there.
        """
        if self.islm is None:
            raise ValidationError("this economy has no IS-LM block")
        level = self.expected_price if price is None else price
        return replace(self, islm=self.islm.calibrated(self.output(level), level, rate))

    def curve(self, curve: Curve) -> EconomicCurve:
        """Bind a drawable curve identifier to this economy.

        The local import keeps the economic equations independent of movement rendering.
        The annotations are resolved at runtime to avoid a module cycle on Python 3.10.
        """
        from macro_viz.panels.movement import Curve, EconomicCurve

        if not isinstance(curve, Curve):
            raise ValidationError("curve must be a Curve member")
        return EconomicCurve(self, curve)
