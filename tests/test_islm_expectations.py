from __future__ import annotations

import pytest
from mosaickit import BraceLayer

from macro_viz.islm import ISLM, ISLMExpectations
from macro_viz.visuals import islm_expectations_canvas


def base() -> ISLM:
    return ISLM(100, 25, 20, 0.5, 10)


def test_nominal_rate_is_the_real_rate_plus_expected_inflation() -> None:
    model = ISLMExpectations(base(), 0.2)

    assert model.real_rate == pytest.approx(model.equilibrium().rate - 0.2)
    assert model.equilibrium().rate > base().equilibrium().rate


def test_zero_expected_inflation_is_the_plain_model() -> None:
    plain = ISLMExpectations(base(), 0.0)

    assert plain.equilibrium() == base().equilibrium()
    assert plain.real_rate == pytest.approx(plain.equilibrium().rate)


def test_higher_expected_inflation_raises_output_and_the_nominal_rate_but_not_by_as_much() -> None:
    low, high = ISLMExpectations(base(), 0.1), ISLMExpectations(base(), 0.3)

    assert high.equilibrium().output > low.equilibrium().output
    gap = high.equilibrium().rate - low.equilibrium().rate
    assert 0 < gap < 0.2
    assert high.real_rate < low.real_rate + 0.2


def test_figure_has_the_wedge_between_real_and_nominal_rate() -> None:
    model = ISLMExpectations(base(), 0.2)
    canvas = islm_expectations_canvas(model, after=model.with_real_money(30))
    found = {layer.id: layer for layer in canvas.snapshot().layers}
    wedge = found["macro.islm.wedge"]

    assert isinstance(wedge, BraceLayer)
    assert (wedge.start, wedge.end) == pytest.approx((model.real_rate, model.equilibrium().rate))
    assert "macro.islm.lm.shifted" in found
