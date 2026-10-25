"""Typed, qualitative movements of the curves in a linked macro diagram.

The public API deliberately describes geometry rather than an economic event.  A caller
chooses the curve, the kind of movement, and its direction.  The linked-panel model applies
one documented schematic preset and then solves the resulting equilibrium.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from macro_viz.errors import ValidationError
from macro_viz.panels.model import LinearFunction, MacroEconomy


class MovementKind(str, Enum):
    """The two changes shown by movement markers."""

    SHIFT = "shift"
    ROTATION = "rotation"


class ShiftDirection(str, Enum):
    """Direction of a parallel translation in the curve's panel."""

    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"


class RotationDirection(str, Enum):
    """Direction of a rotation relative to the panel origin."""

    INWARD = "inward"
    OUTWARD = "outward"


class Curve(str, Enum):
    """A drawable curve that users may move directly."""

    IS = "is"
    LM = "lm"
    AD = "ad"
    AS = "sras"
    LABOR_DEMAND = "labor_demand"
    LABOR_SUPPLY = "labor_supply"
    PRODUCTION = "production"


SHIFTABLE = frozenset((Curve.IS, Curve.LM, Curve.AD, Curve.LABOR_SUPPLY))
ROTATABLE = frozenset((Curve.AS, Curve.LABOR_DEMAND, Curve.PRODUCTION))


@dataclass(frozen=True, slots=True)
class EconomicCurve:
    """A curve bound to the model that supplies its schematic transformation rules."""

    model: MacroEconomy
    id: Curve

    def __post_init__(self) -> None:
        if self.id in (Curve.IS, Curve.LM, Curve.AD) and self.model.islm is None:
            raise ValidationError(f"{self.id.value} needs an IS-LM model")

    def shift(self, direction: ShiftDirection) -> CurveMovement:
        """Return a request to translate this curve using the schematic preset."""
        return CurveMovement(self.id, MovementKind.SHIFT, direction)

    def rotate(self, direction: RotationDirection) -> CurveMovement:
        """Return a request to rotate this curve using the schematic preset."""
        return CurveMovement(self.id, MovementKind.ROTATION, direction)


MovementDirection = ShiftDirection | RotationDirection


@dataclass(frozen=True, slots=True)
class CurveMovement:
    """One explicit movement requested by the caller."""

    curve: Curve
    kind: MovementKind
    direction: MovementDirection

    def __post_init__(self) -> None:
        if self.kind is MovementKind.SHIFT and not isinstance(self.direction, ShiftDirection):
            raise ValidationError("a shift needs a left, right, up, or down direction")
        if self.kind is MovementKind.ROTATION and not isinstance(self.direction, RotationDirection):
            raise ValidationError("a rotation needs an inward or outward direction")
        if self.kind is MovementKind.SHIFT and self.curve not in SHIFTABLE:
            raise ValidationError(f"{self.curve.value} does not support a parallel shift")
        if self.kind is MovementKind.ROTATION and self.curve not in ROTATABLE:
            raise ValidationError(f"{self.curve.value} does not support a rotation")


@dataclass(frozen=True, slots=True)
class _MovementPreset:
    """Visible schematic magnitudes used by the built-in linked-panel model.

    The values are shares of the relevant baseline parameter.  They make a direction legible;
    they are not empirical estimates and are never exposed as measured shock magnitudes.
    """

    translation_share: float = 0.15
    rotation_share: float = 0.50

    def __post_init__(self) -> None:
        if not 0 < self.translation_share < 1:
            raise ValidationError("translation_share must be between 0 and 1")
        if not 0 < self.rotation_share < 1:
            raise ValidationError("rotation_share must be between 0 and 1")


_SCHEMATIC_PRESET = _MovementPreset()


def _signed_share(direction: MovementDirection, share: float) -> float:
    positive = direction in (ShiftDirection.RIGHT, ShiftDirection.UP, RotationDirection.OUTWARD)
    return share if positive else -share


def _one_direction(
    effects: dict[str, MovementDirection], effect: str, direction: MovementDirection
) -> None:
    previous = effects.get(effect)
    if previous is not None and previous is not direction:
        raise ValidationError(f"conflicting curve movements both change {effect}")
    effects[effect] = direction


def apply_movements(
    economy: MacroEconomy,
    movements: tuple[CurveMovement, ...],
    preset: _MovementPreset = _SCHEMATIC_PRESET,
) -> MacroEconomy:
    """Apply supported direct movements to the fixed linked-panel textbook model.

    Several named curves can describe one internally shared change.  For example, an outward
    rotation of production and labour demand is one capital preset, so listing both does not
    apply that preset twice.
    """
    effects: dict[str, MovementDirection] = {}
    for movement in movements:
        curve, kind, direction = movement.curve, movement.kind, movement.direction
        if kind is MovementKind.SHIFT and curve in (Curve.IS, Curve.AD):
            if direction not in (ShiftDirection.LEFT, ShiftDirection.RIGHT):
                raise ValidationError(f"{curve.value} shifts left or right")
            _one_direction(effects, "expenditure", direction)
        elif kind is MovementKind.SHIFT and curve is Curve.LM:
            if direction not in (ShiftDirection.LEFT, ShiftDirection.RIGHT):
                raise ValidationError("lm shifts left or right")
            _one_direction(effects, "money", direction)
        elif kind is MovementKind.SHIFT and curve is Curve.LABOR_SUPPLY:
            if direction not in (ShiftDirection.LEFT, ShiftDirection.RIGHT):
                raise ValidationError("labor supply shifts left or right")
            _one_direction(effects, "labor_supply", direction)
        elif kind is MovementKind.ROTATION and curve in (
            Curve.PRODUCTION,
            Curve.LABOR_DEMAND,
            Curve.AS,
        ):
            _one_direction(effects, "capital", direction)
        else:
            raise ValidationError(
                f"{curve.value} does not support a {kind.value} in the linked-panel preset"
            )

    changed = economy
    capital_direction = effects.get("capital")
    if capital_direction is not None:
        share = _signed_share(capital_direction, preset.rotation_share)
        changed = replace(changed, capital=changed.capital * (1 + share))

    labor_direction = effects.get("labor_supply")
    if labor_direction is not None:
        share = _signed_share(labor_direction, preset.translation_share)
        supply = changed.labor_supply
        changed = replace(
            changed,
            labor_supply=LinearFunction(supply.intercept * (1 - share), supply.slope),
        )

    if "money" in effects or "expenditure" in effects:
        if changed.islm is None:
            raise ValidationError("IS, LM, and AD movements need an IS-LM model")
        block = changed.islm
        money = block.money
        expenditure = block.expenditure
        money_direction = effects.get("money")
        if money_direction is not None:
            money *= 1 + _signed_share(money_direction, preset.translation_share)
        expenditure_direction = effects.get("expenditure")
        if expenditure_direction is not None:
            expenditure *= 1 + _signed_share(expenditure_direction, preset.translation_share)
        changed = replace(changed, islm=replace(block, money=money, expenditure=expenditure))
    return changed


__all__ = [
    "Curve",
    "CurveMovement",
    "EconomicCurve",
    "MovementKind",
    "RotationDirection",
    "ShiftDirection",
    "apply_movements",
]
