"""Keys, sampling and clipping shared by every curve family."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from macro_viz.errors import ValidationError
from macro_viz.panels.curves._types import KEY_DIGITS, Point, Subscripted
from macro_viz.panels.model import P
from macro_viz.panels.scenario import PanelState


def _key(*numbers: float) -> tuple[float, ...]:
    return tuple(round(number, KEY_DIGITS) for number in numbers)


def _first_index(states: Sequence[PanelState], match: Callable[[PanelState], bool], v: str) -> int:
    for state in states:
        if match(state):
            return state.subscript(v)
    raise ValidationError("no step carries this parameter")


def _has_capital(capital: float) -> Callable[[PanelState], bool]:
    return lambda state: _key(state.economy.capital) == _key(capital)


def price_symbol(states: Sequence[PanelState], price: float) -> Subscripted:
    """``p`` with the index of the first step at ``price``, or the expected price ``p^e``."""
    for state in states:
        if _key(state.values[P]) == _key(price):
            return Subscripted("price", state.subscript(P))
    return Subscripted("expected_price")


def _linspace(low: float, high: float, samples: int) -> list[float]:
    if samples < 2:
        raise ValidationError("samples must be at least 2")
    step = (high - low) / (samples - 1)
    return [low + k * step for k in range(samples)]


def clip(points: Sequence[Point], x_max: float, y_max: float) -> tuple[Point, ...]:
    """The part of a polyline inside ``[0, x_max] x [0, y_max]`` (Liang-Barsky on each segment)."""
    kept: list[Point] = []
    for (ax, ay), (bx, by) in zip(points, points[1:], strict=False):
        dx, dy = bx - ax, by - ay
        lo, hi = 0.0, 1.0
        inside = True
        for p, q in ((-dx, ax), (dx, x_max - ax), (-dy, ay), (dy, y_max - ay)):
            if p == 0:
                if q < 0:
                    inside = False
                    break
                continue
            t = q / p
            if p < 0:
                lo = max(lo, t)
            else:
                hi = min(hi, t)
        if not inside or lo > hi:
            continue
        first = (ax + lo * dx, ay + lo * dy)
        last = (ax + hi * dx, ay + hi * dy)
        if not kept or kept[-1] != first:
            kept.append(first)
        kept.append(last)
    if len(kept) < 2:
        raise ValidationError("a curve does not enter the plot; widen the axes")
    return tuple(kept)


def _line(through: Point, slope: float, x_low: float, x_high: float) -> list[Point]:
    """The segment with ``dy/dx = slope`` through a point, from ``x_low`` to ``x_high``."""
    x0, y0 = through
    return [(x_low, y0 + slope * (x_low - x0)), (x_high, y0 + slope * (x_high - x0))]
