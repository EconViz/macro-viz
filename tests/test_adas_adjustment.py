from __future__ import annotations

import pytest
from mosaickit import MarkerLayer

from macro_viz import ValidationError
from macro_viz.adas import (
    AggregateDemand,
    AggregateSupply,
    ASADModel,
    analyze_adjustment,
    analyze_demand_shock,
    analyze_supply_shock,
)
from macro_viz.visuals import adas_adjustment_canvas


def natural() -> ASADModel:
    return ASADModel(AggregateSupply.linear(1.0, 100, 0.6), AggregateDemand(55, 45, 1))


def layers(canvas: object) -> dict[str, object]:
    return {layer.id: layer for layer in canvas.snapshot().layers}  # type: ignore[attr-defined]


def test_money_expansion_ends_at_natural_output_with_a_higher_price() -> None:
    path = analyze_adjustment(analyze_demand_shock(natural(), money=70))

    assert path.medium_run.output == pytest.approx(100)
    assert path.steps[1].equilibrium.output > 100
    assert path.medium_run.price > path.steps[1].equilibrium.price > path.steps[0].equilibrium.price
    assert path.medium_run.price == pytest.approx(path.medium_run.expected_price)


def test_deficit_reduction_lowers_output_then_prices_fall_back() -> None:
    path = analyze_adjustment(analyze_demand_shock(natural(), autonomous=35))

    assert path.steps[1].equilibrium.output < 100
    assert path.medium_run.price < path.steps[0].equilibrium.price


def test_expectation_revisions_converge_toward_natural_output() -> None:
    boom = ASADModel(AggregateSupply.linear(1.0, 100, 0.6), AggregateDemand(80, 45, 1))
    path = analyze_adjustment(boom, rounds=40)
    gaps = [abs(o - 100) for o in path.outputs]

    assert all(b < a for a, b in zip(gaps, gaps[1:], strict=False))
    assert path.outputs[-1] == pytest.approx(100, abs=0.5)
    assert list(path.prices) == sorted(path.prices)


def test_oil_shock_is_stagflation_then_output_recovers() -> None:
    path = analyze_adjustment(analyze_supply_shock(natural(), scale=1.12), rounds=1)

    assert path.steps[1].equilibrium.output < path.steps[0].equilibrium.output
    assert path.steps[1].equilibrium.price > path.steps[0].equilibrium.price
    # a lasting cost increase lowers the natural level of output
    assert path.medium_run.output < 100
    impact = path.steps[1].model.supply
    assert path.medium_run.output == pytest.approx(impact.effective_natural_output)


def test_invalid_rounds_are_rejected() -> None:
    with pytest.raises(ValidationError):
        analyze_adjustment(natural(), rounds=-1)


def test_figure_has_one_point_and_one_supply_curve_per_step() -> None:
    path = analyze_adjustment(analyze_demand_shock(natural(), money=70))
    found = layers(adas_adjustment_canvas(path))

    assert {"macro.adas.point.0", "macro.adas.point.1", "macro.adas.point.2"} <= set(found)
    assert {"macro.adas.supply", "macro.adas.supply.1", "macro.adas.demand.shifted"} <= set(found)
    medium = found["macro.adas.point.2"]
    assert isinstance(medium, MarkerLayer)
    assert medium.points[0] == pytest.approx((path.medium_run.output, path.medium_run.price))
