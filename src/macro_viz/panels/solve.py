"""Root finding for the monotone one-variable equations of the linked-panel models."""

from __future__ import annotations

from collections.abc import Callable

from macro_viz.errors import ValidationError

TOLERANCE = 1e-12
"""Width of the bracket at which bisection stops."""

MAX_ITERATIONS = 200
"""Bisection steps before giving up; far more than a float needs."""

SEARCH_LIMIT = 60
"""How many times a bracket may double before the search gives up."""


def bisect(function: Callable[[float], float], low: float, high: float) -> float:
    """The root of ``function`` in ``[low, high]``; the ends must have opposite signs."""
    f_low, f_high = function(low), function(high)
    if f_low == 0:
        return low
    if f_high == 0:
        return high
    if (f_low > 0) == (f_high > 0):
        raise ValidationError("the equation has no solution between the bounds")
    for _ in range(MAX_ITERATIONS):
        middle = (low + high) / 2
        value = function(middle)
        if value == 0 or (high - low) / 2 < TOLERANCE:
            return middle
        if (value > 0) == (f_low > 0):
            low, f_low = middle, value
        else:
            high = middle
    return (low + high) / 2


def bisect_above(function: Callable[[float], float], low: float, start: float) -> float:
    """The root above ``low`` of a function positive at ``low`` and negative far to the right."""
    high = start
    for _ in range(SEARCH_LIMIT):
        if function(high) < 0:
            return bisect(function, low, high)
        high *= 2
    raise ValidationError("the equation has no solution; check the parameters")
