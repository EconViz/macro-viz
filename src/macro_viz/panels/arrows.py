"""Arrows that show a shift: from one curve to the next, or from one step's point to the next.

Everything is computed from the curves and solved states: an arrow starts on a curve, ends on
the curve it shifts to (at the same ``N``, or at the same height for the curves of ``Y``) and
bows to one side. Nothing is placed by hand; ``ArrowOptions`` sets where along the axis, how far
apart and how much each bows.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from macro_viz.errors import ValidationError
from macro_viz.panels.curves import KEY_DIGITS, VERTICAL, CurveSpec, Point
from macro_viz.panels.layout import ADAS, PanelSpec
from macro_viz.panels.model import P, Y
from macro_viz.panels.scenario import PanelState

SHIFT_FAMILIES = ("labor_demand", "production", "is", "lm", "ad")
"""Families whose shifts get an arrow by default."""


@dataclass(frozen=True, slots=True)
class ArrowOptions:
    """Where and how arrows are drawn. Positions are shares of the axis, bends of the length."""

    at: float = 0.4
    """Where along the stretch two curves share an arrow sits (0 at its start, 1 at its end)."""
    family_at: Mapping[str, float] = field(
        default_factory=lambda: {"labor_demand": 0.15, "production": 0.8, "lm": 0.85}
    )
    """``at`` for single families, where the default does not leave the curves far enough apart."""
    spacing: float = 0.3
    """How far the next arrow of a family sits from the last, in the same units as ``at``."""
    bend: float = 0.35
    gap: float = 0.12
    """Share of an arrow's length left free at each end, so it touches neither curve."""
    samples: int = 24
    families: tuple[str, ...] = SHIFT_FAMILIES
    steps: bool = True
    """Also draw the arrow from one step's point to the next at the same price (AD-AS)."""


@dataclass(frozen=True, slots=True)
class ShiftArrow:
    """A polyline from start to end; the arrowhead is at the end."""

    panel: str
    family: str
    points: tuple[Point, ...]


def _interpolate(points: Sequence[Point], at: float, along: int) -> float | None:
    """The other coordinate where the polyline is at ``at`` on coordinate ``along`` (0 or 1)."""
    other = 1 - along
    for first, second in zip(points, points[1:], strict=False):
        low, high = sorted((first[along], second[along]))
        if low <= at <= high and first[along] != second[along]:
            t = (at - first[along]) / (second[along] - first[along])
            return first[other] + t * (second[other] - first[other])
    return None


def _bowed(start: Point, end: Point, bend: float, samples: int) -> tuple[Point, ...]:
    """A quadratic arc from ``start`` to ``end``, bowing by ``bend`` of the length to the left."""
    (x0, y0), (x1, y1) = start, end
    dx, dy = x1 - x0, y1 - y0
    control = ((x0 + x1) / 2 - bend * dy, (y0 + y1) / 2 + bend * dx)
    points = []
    for k in range(samples):
        t = k / (samples - 1)
        a, b, c = (1 - t) ** 2, 2 * t * (1 - t), t * t
        points.append((a * x0 + b * control[0] + c * x1, a * y0 + b * control[1] + c * y1))
    return tuple(points)


def _shorten(start: Point, end: Point, share: float) -> tuple[Point, Point]:
    dx, dy = end[0] - start[0], end[1] - start[1]
    return (
        (start[0] + share * dx, start[1] + share * dy),
        (end[0] - share * dx, end[1] - share * dy),
    )


def _curve_arrows(
    panel: PanelSpec, curves: Sequence[CurveSpec], lengths: dict[str, float], o: ArrowOptions
) -> list[ShiftArrow]:
    arrows: list[ShiftArrow] = []
    by_family: dict[str, list[CurveSpec]] = {}
    for curve in curves:
        if curve.family in o.families:
            by_family.setdefault(curve.family, []).append(curve)
    for family, members in by_family.items():
        for index, (old, new) in enumerate(zip(members, members[1:], strict=False)):
            share = o.family_at.get(family, o.at) + index * o.spacing
            along = 0 if old.direction == VERTICAL else 1
            low = max(min(p[along] for p in old.points), min(p[along] for p in new.points))
            high = min(max(p[along] for p in old.points), max(p[along] for p in new.points))
            if not low < high:
                continue
            level = low + min(share, 1.0) * (high - low)
            first = _interpolate(old.points, level, along)
            second = _interpolate(new.points, level, along)
            if first is None or second is None:
                continue
            if old.direction == VERTICAL:
                # curves of N shift vertically: read both at one N
                start, end = _shorten((level, first), (level, second), o.gap)
            else:
                start, end = _shorten((first, level), (second, level), o.gap)
            sign = -1 if index % 2 == 0 else 1
            curved = old.direction == VERTICAL and family != "ad"
            points = _bowed(start, end, sign * o.bend, o.samples) if curved else (start, end)
            arrows.append(ShiftArrow(panel.key, family, points))
    return arrows


def _step_arrows(
    panel: PanelSpec, states: Sequence[PanelState], o: ArrowOptions
) -> list[ShiftArrow]:
    arrows = []
    for first, second in zip(states, states[1:], strict=False):
        same_price = round(first.values[P], KEY_DIGITS) == round(second.values[P], KEY_DIGITS)
        if same_price and first.values[Y] != second.values[Y]:
            start, end = _shorten(
                (first.values[Y], first.values[P]), (second.values[Y], second.values[P]), o.gap
            )
            arrows.append(ShiftArrow(panel.key, "step", (start, end)))
    return arrows


def shift_arrows(
    panel: PanelSpec,
    curves: Sequence[CurveSpec],
    states: Sequence[PanelState],
    lengths: dict[str, float],
    options: ArrowOptions,
) -> list[ShiftArrow]:
    """The shift arrows of one panel."""
    if options.samples < 2:
        raise ValidationError("arrow samples must be at least 2")
    arrows = _curve_arrows(panel, [c for c in curves if c.panel == panel.key], lengths, options)
    if options.steps and panel.kind == ADAS:
        arrows += _step_arrows(panel, states, options)
    return arrows
