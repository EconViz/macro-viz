from __future__ import annotations

import pytest

from macro_viz import ValidationError
from macro_viz.keynesian import (
    ConsumptionFunction,
    CurvedDemand,
    Direction,
    KeynesianCross,
    analyze_autonomous_shift,
)


def textbook() -> KeynesianCross:
    return KeynesianCross(ConsumptionFunction(20, 0.6), investment=20, government=30, taxes=20)


def test_consumption_function_and_saving() -> None:
    function = ConsumptionFunction(20, 0.6)

    assert function.consumption(100) == pytest.approx(80)
    assert function.saving(100) == pytest.approx(20)
    assert function.saving_propensity == pytest.approx(0.4)
    assert function.consumption(100) + function.saving(100) == pytest.approx(100)


@pytest.mark.parametrize("autonomous, propensity", [(-1, 0.5), (1, 0), (1, 1), (1, 1.2)])
def test_invalid_consumption_functions_are_rejected(autonomous: float, propensity: float) -> None:
    with pytest.raises(ValidationError):
        ConsumptionFunction(autonomous, propensity)


def test_multiplier_is_one_over_one_minus_c1() -> None:
    assert KeynesianCross(ConsumptionFunction(0, 0.6), 0, 0, 0).multiplier == pytest.approx(2.5)


def test_equilibrium_equates_production_and_demand() -> None:
    model = textbook()
    equilibrium = model.equilibrium()

    assert model.autonomous_spending == pytest.approx(20 + 20 + 30 - 0.6 * 20)
    assert equilibrium.output == pytest.approx(model.autonomous_spending * 2.5)
    assert model.demand(equilibrium.output) == pytest.approx(equilibrium.output)
    assert equilibrium.multiplier == pytest.approx(2.5)


def test_autonomous_shift_moves_output_by_the_multiplier() -> None:
    shift = analyze_autonomous_shift(textbook(), 10)

    assert shift.output_change == pytest.approx(25)
    assert shift.direction is Direction.UP
    assert shift.post.equilibrium().output == pytest.approx(
        shift.baseline.equilibrium().output + 25
    )
    assert analyze_autonomous_shift(textbook(), -4).direction is Direction.DOWN
    assert analyze_autonomous_shift(textbook(), 0).direction is Direction.NONE


def test_adjustment_path_converges_to_the_post_change_equilibrium() -> None:
    shift = analyze_autonomous_shift(textbook(), 10)
    steps = shift.adjustment_path(60)

    assert steps[0].previous_output == pytest.approx(shift.baseline.equilibrium().output)
    assert steps[0].demand == pytest.approx(steps[0].previous_output + 10)
    assert steps[-1].output == pytest.approx(shift.post.equilibrium().output, rel=1e-6)
    assert all(b.output > a.output for a, b in zip(steps, steps[1:], strict=False))
    assert all(step.previous_output < step.output for step in steps)
    with pytest.raises(ValidationError):
        shift.adjustment_path(0)


def test_curved_demand_equilibrium_is_a_root() -> None:
    curved = CurvedDemand(lambda y: 40 + 0.5 * y + 0.0008 * y**2, 0, 400)
    equilibrium = curved.equilibrium()

    assert equilibrium.output == pytest.approx(94.0, abs=0.5)
    assert curved.demand(equilibrium.output) == pytest.approx(equilibrium.output, abs=1e-6)


def test_curved_demand_requires_a_bracket() -> None:
    with pytest.raises(ValidationError):
        CurvedDemand(lambda y: 1000 + y * 0.1, 0, 10).equilibrium()
    with pytest.raises(ValidationError):
        CurvedDemand(lambda y: y, 5, 5)
