from __future__ import annotations

import math
from collections.abc import Iterator
from pathlib import Path

import pytest
from mosaickit import MarkerLayer, PathLayer

from macro_viz import Config, ValidationError
from macro_viz.direction import Direction
from macro_viz.growth import Solow, analyze_change, simulate
from macro_viz.visuals import (
    golden_rule_canvas,
    production_function_canvas,
    solow_canvas,
    solow_growth_rate_canvas,
    solow_level_path_canvas,
    solow_log_path_canvas,
)


@pytest.fixture(autouse=True)
def _reset_config() -> Iterator[None]:
    yield
    Config.reset()


def model(**kw: float) -> Solow:
    values = {"alpha": 0.33, "saving": 0.2, "depreciation": 0.1}
    values.update(kw)
    return Solow.cobb_douglas(**values)


def test_steady_state_matches_the_cobb_douglas_formula() -> None:
    m = model()

    assert m.steady_state() == pytest.approx((0.2 / 0.1) ** (1 / (1 - 0.33)), rel=1e-6)
    assert m.investment(m.steady_state()) == pytest.approx(m.required_investment(m.steady_state()))
    technology = model(population_growth=0.01, tech_growth=0.02)
    assert technology.steady_state() == pytest.approx((0.2 / 0.13) ** (1 / 0.67), rel=1e-6)


def test_golden_rule_saving_equals_alpha() -> None:
    m = model()

    assert m.golden_rule_saving() == pytest.approx(0.33, abs=1e-5)
    assert m.golden_rule_capital() == pytest.approx((0.33 / 0.1) ** (1 / 0.67), rel=1e-4)
    assert m.consumption_at(0.33) > m.consumption_at(0.2) > m.consumption_at(0.1)
    assert m.consumption_at(0.33) > m.consumption_at(0.6)


def test_higher_saving_raises_the_steady_state_and_growth_lowers_it() -> None:
    saving = analyze_change(model(), model(saving=0.35))
    population = analyze_change(model(), model(population_growth=0.05))

    assert (saving.capital_direction, saving.output_direction) == (Direction.UP, Direction.UP)
    assert population.capital_direction is Direction.DOWN


def test_accumulation_moves_capital_toward_the_steady_state_monotonically() -> None:
    m = model()
    steady = m.steady_state()
    below, above = 0.5 * steady, 1.7 * steady

    assert below < m.next_capital(below) < steady
    assert steady < m.next_capital(above) < above
    assert m.next_capital(steady) == pytest.approx(steady)


def test_path_converges_to_the_new_steady_state() -> None:
    base = model(tech_growth=0.02)
    post = base.with_saving(0.35)
    path = simulate(base, post, periods=400, change_period=5)

    assert path.capital[0] == pytest.approx(base.steady_state())
    assert path.capital[5] == path.capital[0]
    assert path.capital[-1] == pytest.approx(post.steady_state(), rel=1e-4)
    assert all(b >= a for a, b in zip(path.capital, path.capital[1:], strict=False))
    rates = path.growth_rates
    assert rates[0] == pytest.approx(0.02, abs=1e-9)
    assert rates[6] > rates[-1] and rates[-1] == pytest.approx(0.02, abs=1e-4)


def test_log_trend_slope_equals_the_growth_rate_of_technology() -> None:
    base = model(tech_growth=0.02)
    path = simulate(base, base.with_saving(0.35), periods=300, change_period=5)
    logs = path.log_output

    assert logs[-1] - logs[-2] == pytest.approx(math.log(1.02), abs=2e-4)
    assert logs[1] - logs[0] == pytest.approx(math.log(1.02), abs=1e-9)


@pytest.mark.parametrize(
    "build",
    [
        lambda: Solow.cobb_douglas(1.0, 0.2, 0.1),
        lambda: Solow.cobb_douglas(0.3, 1.2, 0.1),
        lambda: Solow.cobb_douglas(0.3, 0.2, 0.0),
        lambda: Solow.cobb_douglas(0.3, 0.2, -0.1),
    ],
)
def test_invalid_models_are_rejected(build: object) -> None:
    with pytest.raises(ValidationError):
        build()  # type: ignore[operator]


def test_simulate_validates_its_arguments() -> None:
    with pytest.raises(ValidationError):
        simulate(model(), model(), periods=10, change_period=10)


def layers(canvas: object) -> dict[str, object]:
    return {layer.id: layer for layer in canvas.snapshot().layers}  # type: ignore[attr-defined]


def test_solow_figure_marks_the_steady_state_and_convergence() -> None:
    m = model()
    found = layers(solow_canvas(m, title="Solow"))
    marker = found["macro.growth.steady"]

    assert isinstance(marker, MarkerLayer)
    assert marker.points[0] == pytest.approx((m.steady_state(), m.investment(m.steady_state())))
    assert {"macro.growth.convergence.left", "macro.growth.convergence.right"} <= set(found)
    assert "macro.growth.convergence.left" not in layers(solow_canvas(m, show_convergence=False))
    assert "macro.growth.production" not in layers(solow_canvas(m, show_production=False))


def test_saving_change_moves_the_investment_curve_and_the_steady_state() -> None:
    found = layers(solow_canvas(analyze_change(model(), model(saving=0.35))))

    assert {"macro.growth.investment.shifted", "macro.growth.steady.shifted"} <= set(found)
    assert "macro.growth.required.shifted" not in found
    growth = layers(solow_canvas(analyze_change(model(), model(population_growth=0.05))))
    assert "macro.growth.required.shifted" in growth
    assert "macro.growth.investment.shifted" not in growth


def test_production_function_points_lie_on_the_curve() -> None:
    m = model()
    found = layers(production_function_canvas(m, points=[1.0, 3.0]))
    point = found["macro.growth.point.1"]

    assert isinstance(point, MarkerLayer)
    assert point.points[0] == pytest.approx((3.0, m.output(3.0)))
    path = found["macro.growth.production"]
    assert isinstance(path, PathLayer)
    assert all(b[1] > a[1] for a, b in zip(path.path, path.path[1:], strict=False))
    shifted = layers(production_function_canvas(m, shifted=model(productivity=1.4)))
    assert "macro.growth.production.shifted" in shifted


def test_golden_rule_peak_is_at_the_golden_saving_rate() -> None:
    m = model()
    marker = layers(golden_rule_canvas(m))["macro.growth.golden"]

    assert isinstance(marker, MarkerLayer)
    assert marker.points[0][0] == pytest.approx(m.golden_rule_saving())


def test_time_path_figures_draw_levels_trends_and_rates(tmp_path: Path) -> None:
    base = model(tech_growth=0.02)
    path = simulate(base, base.with_saving(0.35), periods=60, change_period=5)

    level = layers(solow_level_path_canvas(path))
    log = layers(solow_log_path_canvas(path))
    rate = layers(solow_growth_rate_canvas(path))

    assert {"macro.growth.level.old", "macro.growth.level.new"} <= set(level)
    assert {"macro.growth.trend.old", "macro.growth.trend.new"} <= set(log)
    assert "macro.growth.path.rate" in rate
    for index, canvas in enumerate(
        (solow_level_path_canvas(path), solow_log_path_canvas(path), golden_rule_canvas(base))
    ):
        target = tmp_path / f"{index}.svg"
        canvas.save(target)
        assert target.stat().st_size > 0
