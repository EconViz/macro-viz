"""A scenario: the baseline economy and the shocked equilibria drawn on the linked panels.

Every step is the baseline economy after a ``Shock`` (parameters changed) at a price level that
is either given or found where the goods market clears. All panels read the one ``PanelState``
of a step, so a value shared between panels (``N``, ``Y``, ``p`` ...) is a single number.

Two ways to place the IS-LM panel:

* derived: the baseline economy has an ``IsLm`` block, steps with no given price clear the goods
  market, and IS, LM and AD follow from its equations (``R`` is solved);
* sketched (``IsLmSketch``): the textbook picture in which IS and LM are straight lines with
  given slopes through the steps; the lines are drawn, not derived from ``M / p``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace

from macro_viz.errors import ValidationError
from macro_viz.panels.model import MacroEconomy, N, P, R, Shock, W, Y
from macro_viz.panels.movement import (
    Curve,
    CurveMovement,
    MovementKind,
    apply_movements,
)
from macro_viz.panels.solve import SEARCH_LIMIT, bisect

CLEARING_TOLERANCE = 1e-9
"""Relative gap between demand and supply below which a point counts as market clearing."""


@dataclass(frozen=True, slots=True)
class Step:
    """One labelled equilibrium of a scenario.

    ``price`` ``None`` means the goods market clears. ``index`` is the subscript of the
    step's values (``N0``, ``p2``; the step's position when ``None``); ``subscripts`` overrides it
    for single variables.
    """

    label: str
    shock: Shock = field(default_factory=Shock)
    price: float | None = None
    index: int | None = None
    subscripts: Mapping[str, int] = field(default_factory=dict)
    adjust_expectations: bool = False
    """Let the expected price level catch up: ``pe`` becomes the price that clears the goods
    market, so output returns to its natural level (the long run)."""
    movements: tuple[CurveMovement, ...] = ()
    """Direct qualitative curve movements; their visible size comes from the scenario preset."""

    def __post_init__(self) -> None:
        if len(self.label) != 1 or not self.label.isascii() or not self.label.isalpha():
            raise ValidationError("a step label must be one ASCII letter (A-Z or a-z)")
        targets = [(movement.curve, movement.kind) for movement in self.movements]
        if len(set(targets)) != len(targets):
            raise ValidationError("a step cannot move the same curve in the same way twice")


@dataclass(frozen=True, slots=True)
class IsLmSketch:
    """A stylised IS-LM: straight lines with given slopes through the listed steps.

    ``steps`` are the labels of the steps that lie on IS-LM; IS passes through all of them,
    starting at ``rate`` for the first (``R = rate + is_slope * (Y - Y_first)``); each has its own
    LM, parallel with slope ``lm_slope``, through it. ``is_slope`` is negative, ``lm_slope``
    positive.
    """

    steps: tuple[str, ...]
    rate: float
    is_slope: float
    lm_slope: float

    def __post_init__(self) -> None:
        if not self.steps:
            raise ValidationError("an IS-LM sketch needs at least one step")
        if not (self.is_slope < 0 < self.lm_slope):
            raise ValidationError("IS slopes down and LM slopes up")


@dataclass(frozen=True, slots=True)
class PanelState:
    """The solved values of one step; ``R`` is present only where IS and LM cross at ``Y``."""

    label: str
    index: int
    subscripts: Mapping[str, int]
    economy: MacroEconomy
    values: Mapping[str, float]
    clearing: bool

    def subscript(self, variable: str) -> int:
        return self.subscripts.get(variable, self.index)


@dataclass(frozen=True, slots=True)
class Scenario:
    """A baseline economy and its steps; the first step is the baseline equilibrium."""

    baseline: MacroEconomy
    steps: tuple[Step, ...]
    sketch: IsLmSketch | None = None

    def __post_init__(self) -> None:
        if not self.steps:
            raise ValidationError("a scenario needs at least one step")
        labels = [step.label for step in self.steps]
        if len(set(labels)) != len(labels):
            raise ValidationError("step labels must be distinct")
        if self.sketch is not None:
            missing = sorted(set(self.sketch.steps) - set(labels))
            if missing:
                raise ValidationError(f"the IS-LM sketch names unknown steps: {missing}")

    def solve(self) -> tuple[PanelState, ...]:
        """The state of every step, consistent across all panels."""
        states = [self._state(position, step) for position, step in enumerate(self.steps)]
        if self.sketch is None:
            return tuple(states)
        sketch = self.sketch
        by_label = {state.label: state for state in states}
        origin = by_label[sketch.steps[0]].values[Y]
        solved = []
        for state in states:
            if state.label in sketch.steps:
                rate = sketch.rate + sketch.is_slope * (state.values[Y] - origin)
                state = PanelState(
                    state.label,
                    state.index,
                    state.subscripts,
                    state.economy,
                    {**state.values, R: rate},
                    True,
                )
            solved.append(state)
        return tuple(solved)

    def movement_kinds(self) -> Mapping[str, MovementKind]:
        """Movement semantics for rendering, resolved outside the rendering layer.

        Direct requests are authoritative.  Existing parameter-based scenarios are adapted to
        the same typed representation for backwards compatibility.
        """
        direct = {
            movement.curve.value: movement.kind
            for step in self.steps
            for movement in step.movements
        }
        if direct:
            return direct

        adapted: dict[str, MovementKind] = {}
        prices = {step.price for step in self.steps if step.price is not None}
        for step in self.steps:
            shock = step.shock
            if shock.capital is not None:
                adapted[Curve.LABOR_DEMAND.value] = MovementKind.ROTATION
                adapted[Curve.PRODUCTION.value] = MovementKind.ROTATION
            if shock.labor_supply_shift is not None or shock.expected_price is not None:
                adapted[Curve.LABOR_SUPPLY.value] = MovementKind.SHIFT
            if shock.money is not None:
                adapted[Curve.LM.value] = MovementKind.SHIFT
                adapted[Curve.AD.value] = MovementKind.SHIFT
            if shock.expenditure is not None:
                adapted[Curve.IS.value] = MovementKind.SHIFT
                adapted[Curve.AD.value] = MovementKind.SHIFT
        if len(prices) > 1:
            adapted[Curve.LABOR_DEMAND.value] = MovementKind.ROTATION
            adapted[Curve.LM.value] = MovementKind.SHIFT
        return adapted

    def _state(self, position: int, step: Step) -> PanelState:
        economy = step.shock.apply(self.baseline)
        economy = apply_movements(economy, step.movements)
        if step.adjust_expectations:
            economy = _with_correct_expectations(economy)
        clearing = step.price is None
        if step.price is None:
            price = economy.clearing_price()
        else:
            price = step.price
        employment = economy.employment(price)
        values = {
            N: employment,
            W: economy.labor_supply_wage(employment),
            Y: economy.production.output(employment, economy.capital),
            P: price,
        }
        if economy.islm is not None:
            gap = abs(economy.islm.demand_output(price) - values[Y])
            if gap <= CLEARING_TOLERANCE * max(1.0, values[Y]):
                clearing = True
                values[R] = economy.islm.is_rate(values[Y])
        return PanelState(
            step.label,
            position if step.index is None else step.index,
            dict(step.subscripts),
            economy,
            values,
            clearing,
        )


def _with_correct_expectations(economy: MacroEconomy) -> MacroEconomy:
    """The economy with ``pe`` equal to the price level that clears its goods market."""

    known: dict[float, float] = {}

    def gap(expected: float) -> float:
        # the search asks for the same expected price again at every bracket end
        if expected not in known:
            known[expected] = replace(economy, expected_price=expected).clearing_price() - expected
        return known[expected]

    inner = economy.expected_price
    first = gap(inner)
    if first == 0:
        return economy
    factor = 2.0 if first > 0 else 0.5
    for _ in range(SEARCH_LIMIT):
        outer = inner * factor
        if gap(outer) * gap(inner) <= 0:
            low, high = sorted((inner, outer))
            return replace(economy, expected_price=bisect(gap, low, high))
        inner = outer
    raise ValidationError("expectations do not converge; check the parameters")
