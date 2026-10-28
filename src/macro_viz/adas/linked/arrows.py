"""Straight arrows that show a shift from an old equilibrium to a new curve.

Every arrow starts exactly at a solved equilibrium and travels horizontally.  Its arrowhead
stops just before the shifted curve.  Curved arrows are reserved for rotations and therefore
do not belong in this module.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from macro_viz.adas.linked.curves import KEY_DIGITS, CurveSpec, Point
from macro_viz.adas.linked.layout import ADAS, PanelSpec
from macro_viz.adas.linked.model import P, Y
from macro_viz.adas.linked.movement import MovementKind
from macro_viz.adas.linked.scenario import PanelState
from macro_viz.core.errors import ValidationError


@dataclass(frozen=True, slots=True)
class ArrowOptions:
    """Which shift arrows are drawn and how far their heads stop before the new curve."""

    gap: float = 0.12
    """Gap before a destination curve; rotation markers use the same gap at both ends."""
    rotation_clearance: float = 0.035
    """Minimum separation between rotation markers as a share of the panel extent."""
    rotation_search_step: float = 0.015
    """Radial step used while MosaicKit searches inward from the curve tails."""
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


def _shorten_end(start: Point, end: Point, share: float) -> Point:
    """Leave ``start`` untouched and keep the arrowhead clear of the destination curve."""
    dx, dy = end[0] - start[0], end[1] - start[1]
    return end[0] - share * dx, end[1] - share * dy


def _on_curve(curve: CurveSpec, point: Point, y_length: float) -> bool:
    """Whether ``point`` lies on ``curve``, allowing for sampled floating-point geometry."""
    y = _interpolate(curve.points, point[0], 0)
    tolerance = max(y_length, 1.0) * 1e-7
    return y is not None and abs(y - point[1]) <= tolerance


def _old_equilibrium(
    panel: PanelSpec,
    old: CurveSpec,
    new: CurveSpec,
    states: Sequence[PanelState],
    lengths: Mapping[str, float],
) -> Point | None:
    """The last equilibrium on ``old`` before the first equilibrium on ``new`` appears."""
    available = [
        (index, (state.values[panel.x], state.values[panel.y]))
        for index, state in enumerate(states)
        if panel.x in state.values and panel.y in state.values
    ]
    on_new = [index for index, point in available if _on_curve(new, point, lengths[panel.y])]
    before = min(on_new, default=len(states))
    on_old = [
        (index, point)
        for index, point in available
        if index < before and _on_curve(old, point, lengths[panel.y])
    ]
    if not on_old:
        on_old = [
            (index, point) for index, point in available if _on_curve(old, point, lengths[panel.y])
        ]
    return max(on_old, default=(0, None), key=lambda item: item[0])[1]


def _curve_arrows(
    panel: PanelSpec,
    curves: Sequence[CurveSpec],
    states: Sequence[PanelState],
    lengths: Mapping[str, float],
    movement_kinds: Mapping[str, MovementKind],
    o: ArrowOptions,
) -> list[ShiftArrow]:
    arrows: list[ShiftArrow] = []
    by_family: dict[str, list[CurveSpec]] = {}
    for curve in curves:
        if curve.family in movement_kinds:
            by_family.setdefault(curve.family, []).append(curve)
    for family, members in by_family.items():
        for old, new in zip(members, members[1:], strict=False):
            if movement_kinds[family] is MovementKind.ROTATION:
                continue
            start = _old_equilibrium(panel, old, new, states, lengths)
            if start is None:
                continue
            target_x = _interpolate(new.points, start[1], 1)
            if target_x is None or target_x == start[0]:
                continue
            target = (target_x, start[1])
            arrows.append(
                ShiftArrow(panel.key, family, (start, _shorten_end(start, target, o.gap)))
            )
    return arrows


def _step_arrows(
    panel: PanelSpec, states: Sequence[PanelState], o: ArrowOptions
) -> list[ShiftArrow]:
    arrows = []
    for first, second in zip(states, states[1:], strict=False):
        same_price = round(first.values[P], KEY_DIGITS) == round(second.values[P], KEY_DIGITS)
        if same_price and first.values[Y] != second.values[Y]:
            start = (first.values[Y], first.values[P])
            target = (second.values[Y], second.values[P])
            end = _shorten_end(start, target, o.gap)
            arrows.append(ShiftArrow(panel.key, "step", (start, end)))
    return arrows


def shift_arrows(
    panel: PanelSpec,
    curves: Sequence[CurveSpec],
    states: Sequence[PanelState],
    lengths: dict[str, float],
    options: ArrowOptions,
    movement_kinds: Mapping[str, MovementKind] | None = None,
) -> list[ShiftArrow]:
    """The shift arrows of one panel."""
    if not 0 <= options.gap < 1:
        raise ValidationError("arrow gap must be at least 0 and less than 1")
    if options.rotation_clearance < 0 or options.rotation_search_step <= 0:
        raise ValidationError("rotation placement distances must be positive")
    arrows = _curve_arrows(
        panel,
        [c for c in curves if c.panel == panel.key],
        states,
        lengths,
        movement_kinds or {},
        options,
    )
    if options.steps and panel.kind == ADAS:
        arrows += _step_arrows(panel, states, options)
    return arrows
