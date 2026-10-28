"""The state shared by the curve builders of every panel kind."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from macro_viz.adas.linked.curves._geometry import _line, _linspace, clip
from macro_viz.adas.linked.curves._types import CurveOptions, CurveSpec, Point, Subscripted
from macro_viz.adas.linked.curves.ranges import Ranges
from macro_viz.adas.linked.layout import PanelSpec
from macro_viz.adas.linked.model import N, P, Y
from macro_viz.adas.linked.scenario import PanelState, Scenario


class _Base:
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


def _price_for_output(economy, output: float, top: float) -> float:  # type: ignore[no-untyped-def]
    """The price level at which short-run supply offers ``output`` (bisection on ``p``)."""
    from macro_viz.adas.linked.solve import bisect

    floor = economy.price_floor()
    high = max(top, 2 * floor)
    return bisect(lambda p: economy.output(p) - output, floor * (1 + 1e-9), high)
