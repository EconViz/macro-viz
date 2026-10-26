"""The value types of a panel's curves: points, modes, options and specs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum

Point = tuple[float, float]

DEFAULT_SAMPLES = 60
"""Points per curve when the caller does not say."""

KEY_DIGITS = 9
"""Decimal places at which two parameters count as the same curve."""


class Mode(str, Enum):
    """How curves are drawn: from the equations, or as lines through the solved points."""

    SCHEMATIC = "schematic"
    DERIVED = "derived"


VERTICAL, HORIZONTAL = "vertical", "horizontal"
"""The direction in which a family's curves shift (an arrow between them runs this way)."""


@dataclass(frozen=True, slots=True)
class Subscripted:
    """A symbol (id of ``panels.var.<symbol>`` in the locale table) with a step-index subscript."""

    symbol: str
    index: int | None = None


@dataclass(frozen=True, slots=True)
class CurveSpec:
    """A curve ready to draw. ``direction`` is the axis along which the family's curves shift."""

    panel: str
    family: str
    key: tuple[float, ...]
    main: bool
    points: tuple[Point, ...]
    label_id: str
    fields: Mapping[str, Subscripted | int] = field(default_factory=dict)
    direction: str = VERTICAL

    @property
    def end(self) -> Point:
        return max(self.points, key=lambda point: (point[0], point[1]))


@dataclass(frozen=True, slots=True)
class CurveOptions:
    """Choices that change what is drawn but not what is solved."""

    mode: Mode = Mode.SCHEMATIC
    samples: int = DEFAULT_SAMPLES
    span: tuple[float, float] = (0.1, 0.8)
    """The part of the ``N`` axis (as shares of its length) that curves of ``N`` cover."""
    demand_start: float = 0.02
    """Where labour-demand curves begin on the ``N`` axis, as a share of its length."""
    primary_demand_start: float | None = None
    """Optional earlier start for the primary labour-demand curve only."""
    production_from_origin: bool = False
    """Draw production from zero employment instead of the shared state span."""
    reach: float = 0.18
    """How far a straight line runs beyond its outermost point, as a share of the ``Y`` axis."""
    headroom: float = 0.92
    """The share of each axis curves may fill, leaving room for names and the arrowhead."""
    sras: bool = True
    shifted_sras: bool = True
    """Draw the SRAS of later steps too (False: only the first step's)."""
    lras: bool = False
    ad: bool = True
