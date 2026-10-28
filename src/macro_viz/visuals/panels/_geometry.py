"""Rotation arrows and the shifted states they are drawn from."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import replace

from bezierkit import Point as BezierPoint
from bezierkit.construction import RotationConnector
from mosaickit.layout import Rect, place_rotation_marker

from macro_viz.adas.linked import (
    ArrowOptions,
    PanelSpec,
    PanelState,
)
from macro_viz.adas.linked.arrows import ShiftArrow
from macro_viz.adas.linked.curves import (
    CurveSpec,
)
from macro_viz.adas.linked.movement import MovementKind
from macro_viz.core.errors import ValidationError
from macro_viz.visuals.panels._preset import ROTATION_SAMPLES


def _normalise_path(
    points: Sequence[tuple[float, float]], extent: tuple[float, float]
) -> tuple[tuple[float, float], ...]:
    return tuple((x / extent[0], y / extent[1]) for x, y in points)


def _line_intersection(
    first: CurveSpec, second: CurveSpec, extent: tuple[float, float]
) -> tuple[float, float]:
    """Intersection of two curve endpoint chords in normalised panel coordinates."""
    a, b = _normalise_path((first.points[0], first.points[-1]), extent)
    c, d = _normalise_path((second.points[0], second.points[-1]), extent)
    ab = (b[0] - a[0], b[1] - a[1])
    cd = (d[0] - c[0], d[1] - c[1])
    denominator = ab[0] * cd[1] - ab[1] * cd[0]
    if abs(denominator) < 1e-12:
        raise ValidationError("rotation curves must have a common finite pivot")
    offset = (c[0] - a[0], c[1] - a[1])
    share = (offset[0] * cd[1] - offset[1] * cd[0]) / denominator
    return a[0] + share * ab[0], a[1] + share * ab[1]


def _rotation_connector(
    start: tuple[float, float], end: tuple[float, float], pivot: tuple[float, float]
) -> tuple[tuple[float, float], ...]:
    curve = RotationConnector(BezierPoint(*start), BezierPoint(*end), BezierPoint(*pivot)).build()
    parameters = [index / (ROTATION_SAMPLES - 1) for index in range(ROTATION_SAMPLES)]
    return tuple(tuple(point.coords) for point in curve.at_many(parameters))  # type: ignore[misc]


def _rotation_arrows(
    panel: PanelSpec,
    curves: Sequence[CurveSpec],
    lengths: Mapping[str, float],
    kinds: Mapping[str, MovementKind],
    options: ArrowOptions,
) -> list[ShiftArrow]:
    """Place typed rotation markers in the visual layer using display-neutral geometry."""
    extent = lengths[panel.x], lengths[panel.y]
    families: dict[str, list[CurveSpec]] = defaultdict(list)
    for curve in curves:
        if kinds.get(curve.family) is MovementKind.ROTATION:
            families[curve.family].append(curve)

    arrows = []
    for family, members in families.items():
        accepted: list[tuple[tuple[float, float], ...]] = []
        for old, new in zip(members, members[1:], strict=False):
            old_path = _normalise_path(old.points, extent)
            new_path = _normalise_path(new.points, extent)
            if family == "production":
                pivot = (0.0, 0.0)
                old_path = (pivot, *old_path)
                new_path = (pivot, *new_path)
            else:
                pivot = _line_intersection(old, new, extent)
            placement = place_rotation_marker(
                old_path,
                new_path,
                pivot,
                Rect(0.0, 0.0, 1.0, 1.0),
                _rotation_connector,
                accepted=accepted,
                clearance=options.rotation_clearance,
                search_step=options.rotation_search_step,
                minimum_span=options.rotation_clearance,
            )
            if placement is None:
                raise ValidationError(f"could not place a rotation marker for {family}")
            accepted.append(placement.path)
            points = tuple((x * extent[0], y * extent[1]) for x, y in placement.path)
            arrows.append(ShiftArrow(panel.key, family, points))
    return arrows


def _shifted_states(
    states: Sequence[PanelState], origins: Mapping[str, float]
) -> tuple[PanelState, ...]:
    """The states with every value measured from its axis origin."""
    return tuple(
        replace(
            state,
            values={name: value - origins.get(name, 0.0) for name, value in state.values.items()},
        )
        for state in states
    )
