from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from mosaickit import ArrowLayer, BraceLayer, MarkerLayer, PathLayer

from macro_viz import Config
from macro_viz.keynesian import (
    ConsumptionFunction,
    CurvedDemand,
    KeynesianCross,
    analyze_autonomous_shift,
)
from macro_viz.visuals import (
    consumption_function_canvas,
    keynesian_cross_canvas,
    multiplier_canvas,
)


@pytest.fixture(autouse=True)
def _reset_config() -> Iterator[None]:
    yield
    Config.reset()


def model() -> KeynesianCross:
    return KeynesianCross(ConsumptionFunction(20, 0.6), investment=20, government=30, taxes=20)


def layers(canvas: object) -> dict[str, object]:
    return {layer.id: layer for layer in canvas.snapshot().layers}  # type: ignore[attr-defined]


def test_cross_has_stable_ids_and_marks_the_equilibrium() -> None:
    canvas = keynesian_cross_canvas(model(), title="Goods market")
    found = layers(canvas)

    assert {
        "macro.keynesian.production",
        "macro.keynesian.demand",
        "macro.keynesian.demand.label",
        "macro.keynesian.production.label",
        "macro.keynesian.equilibrium",
        "macro.keynesian.equilibrium.label",
        "macro.keynesian.equilibrium.guide.x.mark",
        "macro.keynesian.autonomous",
    } <= set(found)
    assert canvas.spec.title == "Goods market"
    marker = found["macro.keynesian.equilibrium"]
    assert isinstance(marker, MarkerLayer)
    output = model().equilibrium().output
    assert marker.points[0] == pytest.approx((output, output))
    assert isinstance(found["macro.keynesian.autonomous"], BraceLayer)


def test_cross_axes_are_square_and_follow_the_model() -> None:
    small = keynesian_cross_canvas(model())
    larger = keynesian_cross_canvas(model().shifted(30))

    assert small.spec.x_range == small.spec.y_range
    assert larger.spec.x_max > small.spec.x_max
    assert keynesian_cross_canvas(model(), x_max=500).spec.x_max == 500


def test_the_demand_path_lies_on_the_demand_function() -> None:
    demand = layers(keynesian_cross_canvas(model()))["macro.keynesian.demand"]

    assert isinstance(demand, PathLayer)
    assert all(z == pytest.approx(model().demand(y)) for y, z in demand.path)


def test_curved_demand_draws_a_curve_without_the_autonomous_brace() -> None:
    curved = CurvedDemand(lambda y: 40 + 0.5 * y + 0.0008 * y**2, 0, 400)
    found = layers(keynesian_cross_canvas(curved))

    assert "macro.keynesian.autonomous" not in found
    assert "macro.keynesian.autonomous" in layers(
        keynesian_cross_canvas(curved, show_autonomous=True)
    )
    demand = found["macro.keynesian.demand"]
    assert isinstance(demand, PathLayer)
    slopes = [
        (b[1] - a[1]) / (b[0] - a[0]) for a, b in zip(demand.path, demand.path[1:], strict=False)
    ]
    assert slopes[-1] > slopes[0]


def test_multiplier_draws_the_shift_and_the_staircase() -> None:
    shift = analyze_autonomous_shift(model(), 30)
    found = layers(multiplier_canvas(shift, rounds=3))

    assert {
        "macro.keynesian.demand.shifted",
        "macro.keynesian.equilibrium.shifted",
        "macro.keynesian.shift",
        "macro.keynesian.step.3.output",
    } <= set(found)
    assert "macro.keynesian.step.4.output" not in found
    assert isinstance(found["macro.keynesian.step.1.demand"], ArrowLayer)
    assert found["macro.keynesian.demand.shifted"].role.endswith(".shifted")  # type: ignore[attr-defined]
    path_ids = [i for i in layers(multiplier_canvas(shift, show_path=False)) if ".step." in i]
    assert path_ids == []


def test_multiplier_endpoint_is_the_post_change_equilibrium() -> None:
    shift = analyze_autonomous_shift(model(), 30)
    marker = layers(multiplier_canvas(shift))["macro.keynesian.equilibrium.shifted"]

    assert isinstance(marker, MarkerLayer)
    output = shift.post.equilibrium().output
    assert marker.points[0] == pytest.approx((output, output))


def test_consumption_function_has_intercept_and_slope_triangle() -> None:
    function = ConsumptionFunction(20, 0.6)
    found = layers(consumption_function_canvas(function, 200))

    marker = found["macro.keynesian.intercept"]
    assert isinstance(marker, MarkerLayer)
    assert marker.points[0] == (0.0, 20.0)
    run = found["macro.keynesian.slope.run"]
    rise = found["macro.keynesian.slope.rise"]
    assert isinstance(run, PathLayer) and isinstance(rise, PathLayer)
    run_length = run.path[1][0] - run.path[0][0]
    rise_length = rise.path[1][1] - rise.path[0][1]
    assert rise_length == pytest.approx(0.6 * run_length)
    assert "macro.keynesian.slope.run" not in layers(
        consumption_function_canvas(function, 200, show_slope=False)
    )


def test_labels_and_language_come_from_the_locale_table() -> None:
    english = layers(keynesian_cross_canvas(model()))["macro.keynesian.production.label"]
    Config.from_dict({"macro": {"language": "zh-TW"}}).use()
    chinese = layers(keynesian_cross_canvas(model()))["macro.keynesian.production.label"]
    renamed = layers(keynesian_cross_canvas(model(), labels={"keynesian.curve.production": "P"}))

    assert english.text == "Production"  # type: ignore[attr-defined]
    assert chinese.text == "生產"  # type: ignore[attr-defined]
    assert renamed["macro.keynesian.production.label"].text == "P"  # type: ignore[attr-defined]


def test_unknown_label_ids_are_rejected() -> None:
    from macro_viz import ValidationError

    with pytest.raises(ValidationError):
        keynesian_cross_canvas(model(), labels={"no.such.label": "x"})


def test_label_groups_are_nudged_by_the_settings() -> None:
    Config.from_dict(
        {"macro": {"label": {"curve": {"top": "5pt"}, "point": {"right": "3pt"}}}}
    ).use()
    found = layers(keynesian_cross_canvas(model()))

    assert found["macro.keynesian.demand.label"].nudge.dy > 0  # type: ignore[attr-defined]
    assert found["macro.keynesian.equilibrium.label"].nudge.dx > 0  # type: ignore[attr-defined]


def test_figures_render_and_save(tmp_path: Path) -> None:
    shift = analyze_autonomous_shift(model(), 30)
    for index, canvas in enumerate(
        (
            keynesian_cross_canvas(model()),
            multiplier_canvas(shift),
            consumption_function_canvas(ConsumptionFunction(20, 0.6), 200),
        )
    ):
        target = tmp_path / f"figure{index}.svg"
        canvas.save(target)
        assert target.stat().st_size > 0
