"""Counts of the expensive steps, not wall time: a regression shows as a larger count."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator

import pytest
from mosaickit import PathLayer, TextLayer

from macro_viz import Config
from macro_viz.panels import (
    IsLm,
    LinearFunction,
    MacroEconomy,
    QuadraticProduction,
    Scenario,
    Shock,
    Step,
)
from macro_viz.visuals._kit import MacroCanvas, canvas_spec, new_canvas


@pytest.fixture(autouse=True)
def _reset_config() -> Iterator[None]:
    yield
    Config.reset()


def _economy() -> MacroEconomy:
    block = IsLm(0.0, 1.0, 4.0, 0.4, 0.2)
    base = MacroEconomy(
        QuadraticProduction(3.0, 0.2, 1.0), LinearFunction(0.4, 0.25), 1.0, 1.0, block
    )
    return base.calibrated(2.0)


def test_marginal_product_at_is_the_same_arithmetic() -> None:
    production = QuadraticProduction(3.0, 0.2, 0.7)
    curve = production.marginal_product_at(1.3)
    for employment in (0.0, 0.37, 2.5, 11.0):
        assert curve(employment) == production.marginal_product(employment, 1.3)


def test_the_expectation_search_prices_each_expected_level_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: Counter[float] = Counter()
    original = MacroEconomy.clearing_price

    def counting(self: MacroEconomy) -> float:
        calls[self.expected_price] += 1
        return original(self)

    monkeypatch.setattr(MacroEconomy, "clearing_price", counting)
    base = _economy()
    assert base.islm is not None
    shock = Shock(expenditure=1.12 * base.islm.expenditure)
    Scenario(base, (Step("A"), Step("B", shock, adjust_expectations=True))).solve()

    assert calls
    assert max(calls.values()) <= 2  # once in the search, once for the step's final state


def test_curve_names_are_placed_once_however_many_layers_are_added(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    placements = 0
    original = MacroCanvas._place_labels

    def counting(self: MacroCanvas) -> None:
        nonlocal placements
        placements += 1
        original(self)

    monkeypatch.setattr(MacroCanvas, "_place_labels", counting)
    canvas = new_canvas(canvas_spec((0, 10), (0, 10), width=4, height=3, title=None))
    for index in range(1, 6):
        canvas.add(PathLayer(((0, index), (10, index)), id=f"c{index}", role="macro.curve"))
        canvas.add(TextLayer((10, index), f"c{index}", id=f"c{index}.label", role="macro.curve"))
    assert placements == 0

    canvas.snapshot()
    canvas.snapshot()
    assert placements == 1
    canvas.add(PathLayer(((0, 0), (10, 10)), id="more", role="macro.curve"))
    canvas.snapshot()
    assert placements == 2
