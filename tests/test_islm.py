from __future__ import annotations

from collections.abc import Iterator

import pytest
from mosaickit import MarkerLayer, PathLayer

from macro_viz import Config, ValidationError
from macro_viz.direction import Direction
from macro_viz.islm import ISLM, Policy, analyze_fiscal_policy, analyze_monetary_policy
from macro_viz.visuals import islm_canvas


@pytest.fixture(autouse=True)
def _reset_config() -> Iterator[None]:
    yield
    Config.reset()


def model(h: float = 10.0) -> ISLM:
    return ISLM(100, 25, 20, 0.5, h, 1.0)


def test_equilibrium_lies_on_both_curves() -> None:
    m = model()
    e = m.equilibrium()

    assert e.output == pytest.approx(m.is_output(e.rate))
    assert e.output == pytest.approx(m.lm_output(e.rate))
    assert e.rate == pytest.approx((0.5 * 100 - 20) / (0.5 * 25 + 10))


def test_lm_is_vertical_without_rate_demand() -> None:
    m = model(0.0)

    assert m.lm_output(0.0) == m.lm_output(5.0)
    with pytest.raises(ValidationError):
        m.lm_rate(10)


def test_fiscal_expansion_raises_output_and_rate_with_crowding_out() -> None:
    shift = analyze_fiscal_policy(model(), 120)

    assert shift.policy is Policy.FISCAL
    assert (shift.output_direction, shift.rate_direction) == (Direction.UP, Direction.UP)
    assert 0 < shift.after.output - shift.before.output < 20
    assert shift.crowding_out > 0


def test_a_vertical_lm_crowds_out_everything() -> None:
    shift = analyze_fiscal_policy(model(0.0), 120)

    assert shift.after.output == pytest.approx(shift.before.output)
    assert shift.crowding_out == pytest.approx(20)


def test_a_flat_lm_crowds_out_almost_nothing() -> None:
    shift = analyze_fiscal_policy(model(1e6), 120)

    assert shift.crowding_out == pytest.approx(0, abs=1e-3)


def test_monetary_expansion_raises_output_and_lowers_the_rate() -> None:
    shift = analyze_monetary_policy(model(), 32)

    assert (shift.output_direction, shift.rate_direction) == (Direction.UP, Direction.DOWN)
    assert shift.crowding_out == 0


@pytest.mark.parametrize("field", ["sensitivity", "income_demand", "multiplier"])
def test_invalid_parameters_are_rejected(field: str) -> None:
    values = {
        "autonomous": 100,
        "sensitivity": 25,
        "real_money": 20,
        "income_demand": 0.5,
        "rate_demand": 10,
        "multiplier": 1.0,
    }
    values[field] = 0
    with pytest.raises(ValidationError):
        ISLM(**values)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        ISLM(100, 25, 20, 0.5, -1)


def layers(canvas: object) -> dict[str, object]:
    return {layer.id: layer for layer in canvas.snapshot().layers}  # type: ignore[attr-defined]


def test_figure_marks_the_crossing_and_the_shift() -> None:
    plain = layers(islm_canvas(model(), title="IS-LM"))
    fiscal = layers(islm_canvas(analyze_fiscal_policy(model(), 120), show_crowding=True))
    money = layers(islm_canvas(analyze_monetary_policy(model(), 32)))

    point = plain["macro.islm.equilibrium"]
    assert isinstance(point, MarkerLayer)
    e = model().equilibrium()
    assert point.points[0] == pytest.approx((e.output, e.rate))
    assert "macro.islm.is.shifted" in fiscal and "macro.islm.crowding" in fiscal
    assert "macro.islm.lm.shifted" in money and "macro.islm.is.shifted" not in money
    is_path = plain["macro.islm.is"]
    assert isinstance(is_path, PathLayer)
    assert all(b[0] < a[0] for a, b in zip(is_path.path, is_path.path[1:], strict=False))


def test_plain_equilibrium_is_at_the_canvas_centre() -> None:
    canvas = islm_canvas(model())
    point = layers(canvas)["macro.islm.equilibrium"]
    assert isinstance(point, MarkerLayer)
    x, y = point.points[0]

    assert x == pytest.approx(canvas.spec.x_max / 2)
    assert y == pytest.approx(canvas.spec.y_max / 2)

    found = layers(canvas)
    for layer_id in ("macro.islm.is", "macro.islm.lm"):
        path = found[layer_id]
        assert isinstance(path, PathLayer)
        (x0, y0), (x1, y1) = path.path
        screen_slope = (
            abs((y1 - y0) / (x1 - x0))
            * canvas.spec.x_max
            / canvas.spec.y_max
            * canvas.spec.height
            / canvas.spec.width
        )
        assert screen_slope == pytest.approx(1.0)
        assert x1 - x0 < canvas.spec.x_max / 2


def test_figure_needs_a_positive_equilibrium_rate() -> None:
    with pytest.raises(ValidationError):
        islm_canvas(ISLM(100, 25, 60, 0.5, 10))
