"""Typed, renderer-free wage-setting and price-setting model of the natural unemployment rate.

Equation conventions (real wage ``W/P``, unemployment rate ``u`` between 0 and 1)::

    WS:  W/P = ws_scale * F(u, z)     F(u, z) = level + z - slope * u   (decreasing in u)
    PS:  W/P = ps_scale / (1 + m)     horizontal at productivity over one plus the markup
    u_n: F(u_n, z) = ps_scale / (ws_scale * (1 + m))

``z`` collects what raises wages at any unemployment rate (unemployment benefits, minimum wage),
``m`` is the markup of prices over costs, and ``ws_scale`` and ``ps_scale`` are the productivity
levels wage setters expect and firms have (equal in the benchmark, where both equal ``A``). The
natural rate is where the two curves cross. In employment terms ``N = L (1 - u)``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from numbers import Real

from macro_viz.direction import Direction
from macro_viz.errors import ValidationError


def _finite(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValidationError(f"{name} must be a finite number")
    return float(value)


@dataclass(frozen=True, slots=True)
class WagePriceSetting:
    """Wage setting ``ws_scale * (level + z - slope * u)`` and price setting ``ps_scale/(1+m)``."""

    level: float
    slope: float
    benefits: float
    markup: float
    ws_scale: float = 1.0
    ps_scale: float = 1.0

    def __post_init__(self) -> None:
        for name in ("level", "benefits"):
            object.__setattr__(self, name, _finite(name, getattr(self, name)))
        for name in ("slope", "ws_scale", "ps_scale"):
            value = _finite(name, getattr(self, name))
            if value <= 0:
                raise ValidationError(f"{name} must be positive")
            object.__setattr__(self, name, value)
        markup = _finite("markup", self.markup)
        if markup < 0:
            raise ValidationError("markup must not be negative")
        object.__setattr__(self, "markup", markup)
        if not 0 < self.natural_rate() < 1:
            raise ValidationError("the parameters give a natural rate outside (0, 1)")

    def wage_setting(self, unemployment: float) -> float:
        """Real wage wage setters ask at unemployment rate ``unemployment``."""
        return self.ws_scale * (self.level + self.benefits - self.slope * unemployment)

    @property
    def price_setting(self) -> float:
        """Real wage firms can pay, ``ps_scale / (1 + m)``."""
        return self.ps_scale / (1.0 + self.markup)

    def natural_rate(self) -> float:
        """The ``u`` with ``WS(u) = PS``."""
        target = self.price_setting / self.ws_scale
        return (self.level + self.benefits - target) / self.slope

    def real_wage(self) -> float:
        """The real wage at the natural rate."""
        return self.price_setting

    def with_benefits(self, benefits: float) -> WagePriceSetting:
        return replace(self, benefits=benefits)

    def with_markup(self, markup: float) -> WagePriceSetting:
        return replace(self, markup=markup)

    def with_productivity(self, ws_scale: float, ps_scale: float) -> WagePriceSetting:
        """Set the productivity levels of wage and price setting (equal for a common shift)."""
        return replace(self, ws_scale=ws_scale, ps_scale=ps_scale)


@dataclass(frozen=True, slots=True)
class WagePriceShift:
    """Baseline and post-change models with the direction of the natural rate and real wage."""

    baseline: WagePriceSetting
    post: WagePriceSetting
    rate_direction: Direction
    wage_direction: Direction

    @property
    def before(self) -> float:
        return self.baseline.natural_rate()

    @property
    def after(self) -> float:
        return self.post.natural_rate()


def compare(baseline: WagePriceSetting, post: WagePriceSetting) -> WagePriceShift:
    """Compare two parameter sets by natural rate and real wage."""
    tolerance = 1e-12
    return WagePriceShift(
        baseline,
        post,
        Direction.of(post.natural_rate() - baseline.natural_rate(), tolerance),
        Direction.of(post.real_wage() - baseline.real_wage(), tolerance),
    )


def employment(unemployment: float, labor_force: float) -> float:
    """``N = L (1 - u)``."""
    if labor_force <= 0:
        raise ValidationError("labor force must be positive")
    return labor_force * (1.0 - unemployment)
