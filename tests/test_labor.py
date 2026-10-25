from __future__ import annotations

import pytest
from mosaickit import BraceLayer, MarkerLayer

from macro_viz import ValidationError
from macro_viz.direction import Direction
from macro_viz.labor import WagePriceSetting, compare, employment
from macro_viz.visuals import wsps_canvas


def model() -> WagePriceSetting:
    return WagePriceSetting(1.4, 3.0, 0.3, 0.25)


def test_natural_rate_solves_ws_equals_ps() -> None:
    m = model()
    u = m.natural_rate()

    assert m.wage_setting(u) == pytest.approx(m.price_setting)
    assert u == pytest.approx((1.4 + 0.3 - 1 / 1.25) / 3.0)
    assert m.real_wage() == pytest.approx(0.8)


def test_comparative_statics_signs() -> None:
    benefits = compare(model(), model().with_benefits(0.5))
    markup = compare(model(), model().with_markup(0.5))

    assert benefits.rate_direction is Direction.UP and benefits.wage_direction is Direction.NONE
    assert markup.rate_direction is Direction.UP and markup.wage_direction is Direction.DOWN
    assert markup.after > markup.before


def test_equal_productivity_shifts_leave_the_natural_rate_unchanged() -> None:
    shift = compare(model(), model().with_productivity(1.25, 1.25))

    assert shift.rate_direction is Direction.NONE
    assert shift.wage_direction is Direction.UP


def test_unequal_shifts_move_the_natural_rate() -> None:
    wage_up_more = compare(model(), model().with_productivity(1.3, 1.1))

    assert wage_up_more.rate_direction is Direction.UP
    assert compare(model(), model().with_productivity(1.1, 1.3)).rate_direction is Direction.DOWN


def test_employment_is_the_labor_force_less_the_unemployed() -> None:
    assert employment(0.1, 100) == pytest.approx(90)
    with pytest.raises(ValidationError):
        employment(0.1, 0)


@pytest.mark.parametrize(
    "build",
    [
        lambda: WagePriceSetting(1.4, 0, 0.3, 0.25),
        lambda: WagePriceSetting(1.4, 3, 0.3, -0.1),
        lambda: WagePriceSetting(0.2, 3, 0.0, 0.25),
    ],
)
def test_invalid_models_are_rejected(build: object) -> None:
    with pytest.raises(ValidationError):
        build()  # type: ignore[operator]


def layers(canvas: object) -> dict[str, object]:
    return {layer.id: layer for layer in canvas.snapshot().layers}  # type: ignore[attr-defined]


def test_figure_marks_the_natural_rate_and_the_shift() -> None:
    m = model()
    plain = layers(wsps_canvas(m))
    moved = layers(wsps_canvas(compare(m, m.with_benefits(0.5))))

    point = plain["macro.labor.equilibrium"]
    assert isinstance(point, MarkerLayer)
    assert point.points[0] == pytest.approx((m.natural_rate(), m.real_wage()))
    assert {"macro.labor.ws.shifted", "macro.labor.shift.ws"} <= set(moved)
    assert "macro.labor.ps.shifted" not in moved and "macro.labor.shift.ps" not in moved


def test_equal_shifts_keep_the_crossing_at_the_same_rate() -> None:
    m = model()
    found = layers(wsps_canvas(compare(m, m.with_productivity(1.25, 1.25))))

    assert "macro.labor.equilibrium.shifted.guide.x.mark" not in found
    assert {"macro.labor.shift.ws", "macro.labor.shift.ps"} <= set(found)


def test_employment_version_draws_braces_up_to_the_labor_force() -> None:
    found = layers(wsps_canvas(model(), labor_force=100))

    assert isinstance(found["macro.labor.brace.employment"], BraceLayer)
    assert isinstance(found["macro.labor.brace.unemployment"], BraceLayer)
    point = found["macro.labor.equilibrium"]
    assert isinstance(point, MarkerLayer)
    assert point.points[0][0] == pytest.approx(employment(model().natural_rate(), 100))
