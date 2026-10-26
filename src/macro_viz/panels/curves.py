"""The curves of each panel, computed from the solved states; no drawing, no text.

A curve belongs to a *family* (labour demand, SRAS, LM ...) and has a *key*, the parameters
that make it a different curve (price level and capital for labour demand ...). The curve of the
first step is the main one; a curve another step brings is drawn thin. Label text is described
by ``Subscripted`` symbols (a variable and the step index of its subscript) and resolved
against the locale table by the visual builder.

``Mode.DERIVED`` draws each curve from the model equations. ``Mode.SCHEMATIC`` (the textbook
picture) draws straight lines through the solved points instead, so the lines pass through
the dots whatever the curvature of the equations; the solved values are identical in both.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum

from macro_viz.errors import ValidationError
from macro_viz.panels.layout import ADAS, ISLM, LABOR, PRODUCTION, PanelSpec
from macro_viz.panels.model import N, P, R, W, Y
from macro_viz.panels.scenario import PanelState, Scenario

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
    reach: float = 0.18
    """How far a straight line runs beyond its outermost point, as a share of the ``Y`` axis."""
    headroom: float = 0.92
    """The share of each axis curves may fill, leaving room for names and the arrowhead."""
    sras: bool = True
    shifted_sras: bool = True
    """Draw the SRAS of later steps too (False: only the first step's)."""
    lras: bool = False
    ad: bool = True


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


@dataclass(frozen=True, slots=True)
class Ranges:
    """The length of each variable's axis; panels that show a variable share its length."""

    lengths: Mapping[str, float]

    def __getitem__(self, variable: str) -> float:
        return self.lengths[variable]


def axis_lengths(
    states: Sequence[PanelState],
    *,
    extent: float,
    overrides: Mapping[str, float] | None = None,
    natural: bool = False,
) -> Ranges:
    """Axis lengths: ``extent`` times the largest solved value of each variable.

    ``overrides`` fixes a variable's length. ``natural`` also counts natural output.
    """
    lengths: dict[str, float] = {}
    for variable in (N, W, Y, P, R):
        values = [state.values[variable] for state in states if variable in state.values]
        if variable == Y and natural:
            values += [state.economy.natural_output for state in states]
        if values:
            lengths[variable] = extent * max(values)
    lengths.update(overrides or {})
    for variable, length in lengths.items():
        if not length > 0:
            raise ValidationError(f"the axis of {variable} must have a positive length")
    return Ranges(lengths)


class _Builder:
    def __init__(
        self,
        scenario: Scenario,
        states: Sequence[PanelState],
        ranges: Ranges,
        options: CurveOptions,
    ) -> None:
        self.scenario = scenario
        self.states = states
        self.ranges = ranges
        self.options = options
        self.base = states[0]

    def specs(self, panel: PanelSpec) -> list[CurveSpec]:
        build = {
            LABOR: self.labor,
            PRODUCTION: self.production,
            ADAS: self.adas,
            ISLM: self.islm,
        }.get(panel.kind)
        return build(panel) if build is not None else []

    # -- helpers ------------------------------------------------------------------------
    def _unique(
        self, key_of: Callable[[PanelState], tuple[float, ...] | None]
    ) -> list[tuple[tuple[float, ...], list[PanelState]]]:
        groups: dict[tuple[float, ...], list[PanelState]] = {}
        for state in self.states:
            key = key_of(state)
            if key is not None:
                groups.setdefault(key, []).append(state)
        return list(groups.items())

    def _spec(
        self,
        panel: PanelSpec,
        family: str,
        key: tuple[float, ...],
        main: bool,
        points: Sequence[Point],
        label_id: str,
        fields: Mapping[str, Subscripted | int],
        direction: str,
    ) -> CurveSpec:
        box = self.options.headroom
        clipped = clip(points, box * self.ranges[panel.x], box * self.ranges[panel.y])
        return CurveSpec(panel.key, family, key, main, clipped, label_id, fields, direction)

    def _n_grid(self) -> list[float]:
        low, high = self.options.span
        length = self.ranges[N]
        return _linspace(low * length, high * length, self.options.samples)

    # -- labour market and production ---------------------------------------------------
    def labor(self, panel: PanelSpec) -> list[CurveSpec]:
        grid = self._n_grid()
        demand_grid = _linspace(
            self.options.demand_start * self.ranges[N],
            self.options.span[1] * self.ranges[N],
            self.options.samples,
        )
        specs = []
        demand = self._unique(lambda s: _key(s.values[P], s.economy.capital))
        for key, owners in demand:
            state = owners[0]
            price, capital = state.values[P], state.economy.capital
            fields = {
                "price": price_symbol(self.states, price),
                "capital": Subscripted(
                    "capital",
                    _first_index(self.states, _has_capital(capital), "K"),
                ),
            }
            points = [(n, state.economy.labor_demand(n, price)) for n in demand_grid]
            specs.append(
                self._spec(
                    panel,
                    "labor_demand",
                    key,
                    key == demand[0][0],
                    points,
                    "panels.curve.labor_demand",
                    fields,
                    VERTICAL,
                )
            )
        supply = self._unique(
            lambda s: _key(s.economy.expected_price, s.economy.labor_supply.intercept)
        )
        for key, owners in supply:
            state = owners[0]
            pe = state.economy.expected_price
            points = [(n, state.economy.labor_supply_wage(n)) for n in grid]
            fields = {"expected_price": price_symbol(self.states, pe)}
            specs.append(
                self._spec(
                    panel,
                    "labor_supply",
                    key,
                    key == supply[0][0],
                    points,
                    "panels.curve.labor_supply",
                    fields,
                    VERTICAL,
                )
            )
        return specs

    def production(self, panel: PanelSpec) -> list[CurveSpec]:
        grid = self._n_grid()
        groups = self._unique(lambda s: _key(s.economy.capital))
        specs = []
        for key, owners in groups:
            economy = owners[0].economy
            points = [(n, economy.production.output(n, economy.capital)) for n in grid]
            index = owners[0].subscript("K")
            fields = {"capital": Subscripted("capital", index)}
            specs.append(
                self._spec(
                    panel,
                    "production",
                    key,
                    key == groups[0][0],
                    points,
                    "panels.curve.production",
                    fields,
                    VERTICAL,
                )
            )
        return specs

    # -- AD-AS ----------------------------------------------------------------------------
    def _price_grid(self, state: PanelState) -> list[float]:
        economy = state.economy
        top = self.options.headroom * self.ranges[P]
        floor = economy.price_floor()
        return _linspace(floor, max(top, 1.01 * floor), self.options.samples)

    def _straight(
        self,
        family_anchors: dict[tuple[float, ...], list[Point]],
        derived: Callable[[tuple[float, ...]], Callable[[float], float]],
    ) -> dict[tuple[float, ...], list[Point]]:
        """Lines in (Y, p) through each key's anchors; the first with two sets the slope."""
        reach = self.options.reach * self.ranges[Y]
        slopes: dict[tuple[float, ...], float] = {}
        for key, anchors in family_anchors.items():
            distinct = sorted(set(anchors))
            if len(distinct) >= 2:
                (x1, y1), (x2, y2) = distinct[0], distinct[-1]
                slopes[key] = (y2 - y1) / (x2 - x1)
        shared = next(iter(slopes.values()), None)
        lines: dict[tuple[float, ...], list[Point]] = {}
        for key, anchors in family_anchors.items():
            if key in slopes:
                slope = slopes[key]
            elif shared is not None:
                slope = shared
            else:
                price_of = derived(key)
                x0, y0 = anchors[0]
                step = 1e-4 * self.ranges[Y]
                slope = (price_of(x0 + step) - price_of(x0 - step)) / (2 * step)
            low = min(x for x, _ in anchors) - reach
            high = max(x for x, _ in anchors) + reach
            lines[key] = _line(anchors[0], slope, low, high)
        return lines

    def adas(self, panel: PanelSpec) -> list[CurveSpec]:
        o = self.options
        specs: list[CurveSpec] = []
        schematic = o.mode is Mode.SCHEMATIC
        top = o.headroom * self.ranges[P]
        if o.sras:
            groups = self._unique(lambda s: _key(s.economy.capital, s.economy.expected_price))
            if not o.shifted_sras:
                groups = groups[:1]
            curves: dict[tuple[float, ...], list[Point]] = {}
            if schematic:
                economies = {key: owners[0].economy for key, owners in groups}
                anchors = {
                    key: [(s.values[Y], s.values[P]) for s in owners] for key, owners in groups
                }

                def inverse(key: tuple[float, ...]) -> Callable[[float], float]:
                    economy = economies[key]
                    return lambda y: _price_for_output(economy, y, top)

                curves = self._straight(anchors, inverse)
            else:
                for key, owners in groups:
                    economy = owners[0].economy
                    curves[key] = [(economy.output(p), p) for p in self._price_grid(owners[0])]
            for key, owners in groups:
                state = owners[0]
                fields = {
                    "capital": Subscripted("capital", state.subscript("K")),
                    "expected_price": price_symbol(self.states, state.economy.expected_price),
                }
                specs.append(
                    self._spec(
                        panel,
                        "sras",
                        key,
                        key == groups[0][0],
                        curves[key],
                        "panels.curve.sras",
                        fields,
                        HORIZONTAL,
                    )
                )
        if o.lras:
            groups = self._unique(lambda s: _key(s.economy.natural_output))
            for key, owners in groups:
                y = owners[0].economy.natural_output
                specs.append(
                    self._spec(
                        panel,
                        "lras",
                        key,
                        key == groups[0][0],
                        [(y, 0.0), (y, top / o.headroom)],
                        "panels.curve.lras",
                        {},
                        HORIZONTAL,
                    )
                )
        if o.ad:
            specs += self._demand(panel)
        return specs

    def _demand(self, panel: PanelSpec) -> list[CurveSpec]:
        clearing = [s for s in self.states if s.clearing]
        if not clearing:
            return []
        sketch = self.scenario.sketch is not None
        if sketch:
            groups: list[tuple[tuple[float, ...], list[PanelState]]] = [((), clearing)]
        else:
            groups = [
                (key, owners)
                for key, owners in self._unique(
                    lambda s: (
                        _key(s.economy.islm.money, s.economy.islm.expenditure)
                        if s.clearing and s.economy.islm is not None
                        else None
                    )
                )
            ]
        specs = []
        curves: dict[tuple[float, ...], list[Point]] = {}
        if self.options.mode is Mode.SCHEMATIC or sketch:
            anchors = {key: [(s.values[Y], s.values[P]) for s in owners] for key, owners in groups}
            islms = {key: owners[0].economy.islm for key, owners in groups}

            def inverse(key: tuple[float, ...]) -> Callable[[float], float]:
                islm = islms[key]
                if islm is None:
                    raise ValidationError("a single point does not fix a sketched AD")
                return lambda y: islm.demand_price(y)

            curves = self._straight(anchors, inverse)
        else:
            for key, owners in groups:
                islm = owners[0].economy.islm
                assert islm is not None
                grid = self._price_grid(owners[0])
                curves[key] = [(islm.demand_output(p), p) for p in reversed(grid)]
        for key, owners in groups:
            main = key == groups[0][0]
            index = owners[0].subscript(P)
            fields = {"index": index}
            specs.append(
                self._spec(
                    panel,
                    "ad",
                    key,
                    main,
                    curves[key],
                    "panels.curve.ad" if main else "panels.curve.ad_shifted",
                    fields,
                    HORIZONTAL,
                )
            )
        return specs

    # -- IS-LM ----------------------------------------------------------------------------
    def islm(self, panel: PanelSpec) -> list[CurveSpec]:
        on = [s for s in self.states if R in s.values]
        if not on:
            return []
        reach = self.options.reach * self.ranges[Y]
        lo = min(s.values[Y] for s in on) - reach
        hi = max(s.values[Y] for s in on) + reach
        sketch = self.scenario.sketch
        specs: list[CurveSpec] = []
        if sketch is not None:
            origin = on[0]
            is_line = _line((origin.values[Y], origin.values[R]), sketch.is_slope, lo, hi)
            specs.append(
                self._spec(panel, "is", (), True, is_line, "panels.curve.is", {}, HORIZONTAL)
            )
            for state in on:
                line = _line(
                    (state.values[Y], state.values[R]),
                    sketch.lm_slope,
                    state.values[Y] - reach,
                    state.values[Y] + reach,
                )
                specs.append(self._lm(panel, state, line, state is on[0]))
            return specs
        groups = self._unique(
            lambda s: _key(s.economy.islm.expenditure) if R in s.values and s.economy.islm else None
        )
        for key, owners in groups:
            islm = owners[0].economy.islm
            assert islm is not None
            line = [(y, islm.is_rate(y)) for y in (lo, hi)]
            main = key == groups[0][0]
            specs.append(
                self._spec(
                    panel,
                    "is",
                    key,
                    main,
                    line,
                    "panels.curve.is" if main else "panels.curve.is_shifted",
                    {"index": owners[0].index},
                    HORIZONTAL,
                )
            )
        lms = self._unique(
            lambda s: (
                _key(s.economy.islm.money, s.values[P])
                if R in s.values and s.economy.islm
                else None
            )
        )
        for key, owners in lms:
            state = owners[0]
            islm = state.economy.islm
            assert islm is not None
            price = state.values[P]
            line = [
                (y, islm.lm_rate(y, price))
                for y in (state.values[Y] - reach, state.values[Y] + reach)
            ]
            specs.append(self._lm(panel, state, line, key == lms[0][0]))
        return specs

    def _lm(
        self, panel: PanelSpec, state: PanelState, line: Sequence[Point], main: bool
    ) -> CurveSpec:
        fields = {
            "money": Subscripted("money", self.base.subscript(P)),
            "price": price_symbol(self.states, state.values[P]),
        }
        return self._spec(
            panel, "lm", _key(state.values[P]), main, line, "panels.curve.lm", fields, HORIZONTAL
        )


def _price_for_output(economy, output: float, top: float) -> float:  # type: ignore[no-untyped-def]
    """The price level at which short-run supply offers ``output`` (bisection on ``p``)."""
    from macro_viz.panels.solve import bisect

    floor = economy.price_floor()
    high = max(top, 2 * floor)
    return bisect(lambda p: economy.output(p) - output, floor * (1 + 1e-9), high)


def curve_specs(
    panel: PanelSpec,
    scenario: Scenario,
    states: Sequence[PanelState],
    ranges: Ranges,
    options: CurveOptions,
) -> list[CurveSpec]:
    """Every curve of ``panel`` for the solved ``states``."""
    return _Builder(scenario, states, ranges, options).specs(panel)


def sample_rate(curve: CurveSpec) -> float:
    """The length of the curve's polyline (used to place arrows along it)."""
    return sum(math.dist(a, b) for a, b in zip(curve.points, curve.points[1:], strict=False))
