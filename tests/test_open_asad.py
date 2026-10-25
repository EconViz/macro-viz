from __future__ import annotations

import pytest

from macro_viz import ValidationError
from macro_viz.adas import AggregateDemand, AggregateSupply, ASADModel, Gap, analyze_adjustment
from macro_viz.direction import Direction
from macro_viz.open_economy import analyze_devaluation


def slump() -> ASADModel:
    return ASADModel(AggregateSupply.linear(1.0, 100, 0.6), AggregateDemand(35, 45, 1))


def test_starting_below_natural_output_adjustment_ends_at_natural_output() -> None:
    assert slump().equilibrium().gap is Gap.RECESSIONARY
    path = analyze_adjustment(slump(), rounds=1)

    assert path.medium_run.output == pytest.approx(100)
    assert path.steps[-1].equilibrium.output > path.steps[0].equilibrium.output
    assert path.steps[-1].equilibrium.price < path.steps[0].equilibrium.price


def test_devaluation_shifts_demand_right_and_can_overshoot_natural_output() -> None:
    shift = analyze_devaluation(slump(), 0.4, exchange_effect=50)

    assert shift.post.demand.autonomous == pytest.approx(35 + 20)
    assert (shift.output_direction, shift.price_direction) == (Direction.UP, Direction.UP)
    assert shift.after.output > 100 or shift.after.output > shift.before.output


def test_no_devaluation_changes_nothing() -> None:
    shift = analyze_devaluation(slump(), 0.0, exchange_effect=50)

    assert shift.output_direction is Direction.NONE


def test_invalid_arguments_are_rejected() -> None:
    with pytest.raises(ValidationError):
        analyze_devaluation(slump(), -0.1, exchange_effect=50)
    with pytest.raises(ValidationError):
        analyze_devaluation(slump(), 0.1, exchange_effect=-1)
