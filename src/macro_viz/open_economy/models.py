"""Typed, renderer-free open-economy goods market.

Equation conventions (real quantities; the real exchange rate is held in ``exports`` and
``import_propensity``)::

    Z  = C + I + G + X - IM        demand for domestic goods
    IM = m * Y                     imports rise with income; m is the import propensity
    NX = X - m * Y                 net exports
    Y  = Z                         equilibrium: Y = (A + X) / (1 - c1 + m)

``A`` is autonomous domestic spending of the closed-economy model, ``X`` exports (foreign demand
and the real exchange rate act through it). The open-economy multiplier ``1 / (1 - c1 + m)`` is
smaller than the closed-economy one. A real depreciation raises ``X`` and lowers ``m``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from numbers import Real

from macro_viz.core.direction import Direction
from macro_viz.core.errors import ValidationError
from macro_viz.islm.models import ISLM
from macro_viz.keynesian.models import GoodsMarketEquilibrium, KeynesianCross


def _finite(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValidationError(f"{name} must be a finite number")
    return float(value)


@dataclass(frozen=True, slots=True)
class OpenEconomy:
    """A Keynesian cross with imports ``m * Y`` and exports ``X``."""

    domestic: KeynesianCross
    exports: float
    import_propensity: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "exports", _finite("exports", self.exports))
        m = _finite("import propensity", self.import_propensity)
        if m < 0:
            raise ValidationError("import propensity must not be negative")
        object.__setattr__(self, "import_propensity", m)

    @property
    def multiplier(self) -> float:
        """``1 / (1 - c1 + m)``."""
        return 1.0 / (1.0 - self.domestic.consumption.propensity + self.import_propensity)

    def demand(self, output: float) -> float:
        """Demand for domestic goods at ``output``."""
        return self.domestic.demand(output) + self.exports - self.import_propensity * output

    def net_exports(self, output: float) -> float:
        return self.exports - self.import_propensity * output

    def equilibrium(self) -> GoodsMarketEquilibrium:
        a = self.domestic.autonomous_spending + self.exports
        output = self.multiplier * a
        return GoodsMarketEquilibrium(output, output, self.multiplier)

    def trade_balance(self) -> float:
        """Net exports at the equilibrium output."""
        return self.net_exports(self.equilibrium().output)

    def balanced_trade_output(self) -> float:
        """The output at which net exports are zero, ``X / m``."""
        if self.import_propensity == 0:
            raise ValidationError("without imports net exports never reach zero")
        return self.exports / self.import_propensity

    def with_government(self, government: float) -> OpenEconomy:
        return replace(self, domestic=replace(self.domestic, government=government))

    def with_exports(self, exports: float) -> OpenEconomy:
        return replace(self, exports=exports)

    def with_import_propensity(self, import_propensity: float) -> OpenEconomy:
        return replace(self, import_propensity=import_propensity)


@dataclass(frozen=True, slots=True)
class OpenEconomyShift:
    """Baseline and post-change open economies with the direction of output and trade."""

    baseline: OpenEconomy
    post: OpenEconomy
    output_direction: Direction
    trade_direction: Direction


def compare(baseline: OpenEconomy, post: OpenEconomy) -> OpenEconomyShift:
    tolerance = 1e-12
    return OpenEconomyShift(
        baseline,
        post,
        Direction.of(post.equilibrium().output - baseline.equilibrium().output, tolerance),
        Direction.of(post.trade_balance() - baseline.trade_balance(), tolerance),
    )


@dataclass(frozen=True, slots=True)
class InterestParity:
    """Linear interest parity: ``E = expected_rate - slope * (i - foreign_rate)``.

    ``E`` is the price of domestic currency, so a higher ``E`` is an appreciation. The line is
    anchored at ``E = expected_rate`` where the domestic rate ``i`` equals the foreign rate.
    """

    foreign_rate: float
    expected_rate: float
    slope: float

    def __post_init__(self) -> None:
        for name in ("foreign_rate", "expected_rate"):
            object.__setattr__(self, name, _finite(name, getattr(self, name)))
        slope = _finite("slope", self.slope)
        if slope <= 0:
            raise ValidationError("slope must be positive")
        object.__setattr__(self, "slope", slope)

    def exchange_rate(self, rate: float) -> float:
        return self.expected_rate - self.slope * (rate - self.foreign_rate)

    def rate(self, exchange_rate: float) -> float:
        """The interest rate consistent with ``exchange_rate``."""
        return self.foreign_rate + (self.expected_rate - exchange_rate) / self.slope


@dataclass(frozen=True, slots=True)
class OpenISLM:
    """IS-LM with the exchange rate: ``IS: Y = m (a - b i) - g E`` and interest parity.

    ``exchange_effect`` ``g`` > 0 is how much an appreciation lowers demand (through net exports).
    Under *floating* rates ``E`` follows parity and the economy is the IS-LM model with a steeper
    IS curve; under a *fixed* rate ``i`` is pinned at the foreign rate and the LM curve adjusts.
    """

    base: ISLM
    parity: InterestParity
    exchange_effect: float

    def __post_init__(self) -> None:
        g = _finite("exchange effect", self.exchange_effect)
        if g < 0:
            raise ValidationError("exchange effect must not be negative")
        object.__setattr__(self, "exchange_effect", g)

    def floating_model(self) -> ISLM:
        """The IS-LM model in ``(Y, i)`` once ``E`` is replaced by parity."""
        base, g, parity = self.base, self.exchange_effect, self.parity
        # Y = m (a - b i) - g (e - k (i - i*)) = m (a - (b - g k / m) i) - g (e + k i*)
        sensitivity = base.sensitivity - g * parity.slope / base.multiplier
        if sensitivity <= 0:
            raise ValidationError("the exchange-rate effect makes IS slope upward")
        autonomous = (
            base.autonomous
            - g * (parity.expected_rate + parity.slope * parity.foreign_rate) / base.multiplier
        )
        return replace(base, autonomous=autonomous, sensitivity=sensitivity)

    def equilibrium(self) -> tuple[float, float, float]:
        """Floating regime: ``(Y, i, E)``."""
        e = self.floating_model().equilibrium()
        return e.output, e.rate, self.parity.exchange_rate(e.rate)

    def fixed_equilibrium(self) -> tuple[float, float, float]:
        """Fixed regime with ``E = E_fixed`` implied by ``i = i*``: ``(Y, i*, E)``."""
        rate = self.parity.foreign_rate
        exchange = self.parity.exchange_rate(rate)
        output = (
            self.base.multiplier * (self.base.autonomous - self.base.sensitivity * rate)
            - self.exchange_effect * exchange
        )
        return output, rate, exchange

    def with_base(self, base: ISLM) -> OpenISLM:
        return replace(self, base=base)
