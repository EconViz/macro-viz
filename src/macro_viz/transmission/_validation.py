"""Shared validation for renderer-free transmission models."""

from __future__ import annotations

import math
from numbers import Real

from macro_viz.errors import ValidationError


def finite_number(name: str, value: object) -> float:
    """Return *value* as a finite float."""
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValidationError(f"{name} must be a finite number")
    return float(value)


def positive_number(name: str, value: object) -> float:
    """Return *value* as a finite, strictly positive float."""
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValidationError(f"{name} must be positive")
    number = float(value)
    if number <= 0:
        raise ValidationError(f"{name} must be positive")
    return number


def sweep_values(
    name: str, values: tuple[float, ...], *, positive: bool = False
) -> tuple[float, ...]:
    """Validate and normalize the distinct values of a comparative-static sweep."""
    if len(values) < 2:
        raise ValidationError(f"{name} needs at least two values")
    checked = tuple(finite_number(f"every {name} value", value) for value in values)
    if positive and any(value <= 0 for value in checked):
        raise ValidationError(f"every {name} value must be positive")
    if len(set(checked)) != len(checked):
        raise ValidationError(f"{name} values must be distinct")
    return checked
