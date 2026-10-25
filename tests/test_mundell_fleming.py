from __future__ import annotations

import pytest
from mosaickit import MarkerLayer

from macro_viz import ValidationError
from macro_viz.islm import ISLM
from macro_viz.open_economy import InterestParity, OpenISLM
from macro_viz.visuals import interest_parity_canvas, open_islm_canvas


def parity() -> InterestParity:
    return InterestParity(0.4, 100, 40)


def model(g: float = 0.2) -> OpenISLM:
    return OpenISLM(ISLM(100, 25, 20, 0.5, 10), parity(), g)


def test_parity_is_anchored_and_invertible() -> None:
    p = parity()

    assert p.exchange_rate(0.4) == 100
    assert p.rate(p.exchange_rate(0.7)) == pytest.approx(0.7)
    assert p.exchange_rate(0.5) < p.exchange_rate(0.3)


def test_floating_equilibrium_satisfies_parity_and_the_open_is_curve() -> None:
    y, i, e = model().equilibrium()
    base = model().base

    assert e == pytest.approx(parity().exchange_rate(i))
    assert y == pytest.approx(base.multiplier * (base.autonomous - base.sensitivity * i) - 0.2 * e)


def test_fiscal_expansion_appreciates_the_currency_under_floating_rates() -> None:
    before = model().equilibrium()
    after = model().with_base(model().base.with_autonomous(120)).equilibrium()

    assert after[1] > before[1]
    assert after[2] < before[2] or after[2] != before[2]
    assert after[0] > before[0]


def test_fixed_rate_pins_the_rate_and_money_does_not_matter() -> None:
    first = model().fixed_equilibrium()
    second = model().with_base(model().base.with_real_money(40)).fixed_equilibrium()

    assert first[1] == parity().foreign_rate
    assert first == second


def test_invalid_inputs_are_rejected() -> None:
    with pytest.raises(ValidationError):
        InterestParity(0.4, 100, 0)
    with pytest.raises(ValidationError):
        model(g=5).floating_model()


def test_figures() -> None:
    canvas = interest_parity_canvas(parity())
    found = {layer.id: layer for layer in canvas.snapshot().layers}
    anchor = found["macro.parity.anchor"]

    assert isinstance(anchor, MarkerLayer)
    assert anchor.points[0] == (100, 0.4)
    moved = {layer.id for layer in open_islm_canvas(model(), fiscal=120).snapshot().layers}
    assert "macro.islm.is.shifted" in moved
