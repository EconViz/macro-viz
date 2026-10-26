from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from mosaickit import ArrowLayer, AxisMarkLayer, MarkerLayer, PathLayer, PointLabelLayer

from macro_viz import Config, ValidationError
from macro_viz.adas import (
    AggregateDemand,
    AggregateSupply,
    ASADModel,
    analyze_demand_shock,
    analyze_supply_shock,
)
from macro_viz.visuals import adas_canvas, aggregate_demand_canvas, aggregate_supply_canvas


@pytest.fixture(autouse=True)
def _reset_config() -> Iterator[None]:
    yield
    Config.reset()


def supply() -> AggregateSupply:
    return AggregateSupply.linear(1.0, 100, 0.6)


def demand() -> AggregateDemand:
    return AggregateDemand(80, 45, 1)


def model() -> ASADModel:
    return ASADModel(supply(), demand())


def layers(canvas: object) -> dict[str, object]:
    return {layer.id: layer for layer in canvas.snapshot().layers}  # type: ignore[attr-defined]


def test_equilibrium_figure_has_curves_natural_output_and_both_points() -> None:
    canvas = adas_canvas(model(), title="AS-AD")
    found = layers(canvas)

    assert {
        "macro.adas.supply",
        "macro.adas.supply.label",
        "macro.adas.demand",
        "macro.adas.demand.label",
        "macro.adas.natural",
        "macro.adas.equilibrium",
        "macro.adas.anchor",
        "macro.adas.equilibrium.guide.x.mark",
    } <= set(found)
    assert canvas.spec.title == "AS-AD"
    point = found["macro.adas.equilibrium"]
    assert isinstance(point, MarkerLayer)
    equilibrium = model().equilibrium()
    assert point.points[0] == pytest.approx((equilibrium.output, equilibrium.price))
    anchor = found["macro.adas.anchor"]
    assert isinstance(anchor, MarkerLayer)
    assert anchor.points[0] == pytest.approx((100, 1.0))
    assert "macro.adas.natural" not in layers(adas_canvas(model(), show_natural_output=False))


def test_steady_equilibrium_is_at_the_canvas_centre() -> None:
    steady = ASADModel(
        AggregateSupply.linear(1.0, 20.0, 0.35),
        AggregateDemand(5.0, 12.0, 1.25),
    )
    canvas = adas_canvas(steady)
    found = layers(canvas)
    point = found["macro.adas.equilibrium"]
    assert isinstance(point, MarkerLayer)
    x, y = point.points[0]

    assert x == pytest.approx(canvas.spec.x_max / 2)
    assert y == pytest.approx(canvas.spec.y_max / 2)
    assert "macro.adas.anchor" not in found
    label = found["macro.adas.equilibrium.label"]
    assert isinstance(label, PointLabelLayer)
    assert label.text == "$A=B$"
    output_mark = found["macro.adas.natural.mark"]
    assert isinstance(output_mark, AxisMarkLayer)
    assert output_mark.label == "Y=Y_n"
    assert "macro.adas.equilibrium.guide.x.mark" not in found
    price_mark = found["macro.adas.expected.y.mark"]
    assert isinstance(price_mark, AxisMarkLayer)
    assert price_mark.label == "p=p^e"
    assert "macro.adas.equilibrium.guide.y.mark" not in found


def test_the_curves_lie_on_the_model_equations() -> None:
    found = layers(adas_canvas(model()))
    supply_path, demand_path = found["macro.adas.supply"], found["macro.adas.demand"]

    assert isinstance(supply_path, PathLayer) and isinstance(demand_path, PathLayer)
    assert all(p == pytest.approx(supply().price(y)) for y, p in supply_path.path)
    assert all(p == pytest.approx(demand().price(y)) for y, p in demand_path.path)
    assert all(b[1] < a[1] for a, b in zip(demand_path.path, demand_path.path[1:], strict=False))


def test_demand_shock_draws_the_new_demand_curve_and_the_new_crossing() -> None:
    shock = analyze_demand_shock(model(), autonomous=100)
    found = layers(adas_canvas(shock))

    assert {
        "macro.adas.demand.shifted",
        "macro.adas.shift",
        "macro.adas.equilibrium.shifted",
    } <= set(found)
    assert "macro.adas.supply.shifted" not in found
    marker = found["macro.adas.equilibrium.shifted"]
    assert isinstance(marker, MarkerLayer)
    after = shock.after
    assert marker.points[0] == pytest.approx((after.output, after.price))


def test_supply_shock_with_ambiguous_demand_marks_both_directions() -> None:
    shock = analyze_supply_shock(model(), scale=0.8)
    found = layers(adas_canvas(shock, ambiguous_demand=True))

    assert "macro.adas.supply.shifted" in found
    assert found["macro.adas.ambiguous.left.label"].text == "?"  # type: ignore[attr-defined]
    assert isinstance(found["macro.adas.ambiguous.right"], ArrowLayer)
    assert "macro.adas.ambiguous.left" not in layers(adas_canvas(shock))


def test_employment_note_names_the_derived_quantity() -> None:
    assert "macro.adas.employment" in layers(adas_canvas(model(), productivity=1.0))
    assert "macro.adas.employment" not in layers(adas_canvas(model()))


def test_supply_figure_marks_the_anchor_and_its_shift() -> None:
    plain = layers(aggregate_supply_canvas(supply()))
    moved = layers(aggregate_supply_canvas(supply(), shifted=supply().with_expected_price(1.2)))

    anchor = plain["macro.adas.anchor"]
    assert isinstance(anchor, MarkerLayer)
    assert anchor.points[0] == pytest.approx((100, 1.0))
    assert "macro.adas.supply.shifted" not in plain
    shifted = moved["macro.adas.anchor.shifted"]
    assert isinstance(shifted, MarkerLayer)
    assert shifted.points[0] == pytest.approx((100, 1.2))


def test_demand_figure_draws_each_shifted_curve_with_its_caption() -> None:
    found = layers(
        aggregate_demand_canvas(
            demand(),
            [demand().with_autonomous(100), demand().with_money(30)],
            captions=["More spending", "Less money"],
            x_max=240,
            y_max=2.2,
        )
    )

    assert {"macro.adas.demand.shifted", "macro.adas.demand.shifted.1"} <= set(found)
    assert found["macro.adas.shift.caption"].text == "More spending"  # type: ignore[attr-defined]
    assert found["macro.adas.shift.1.caption"].text == "Less money"  # type: ignore[attr-defined]
    with pytest.raises(ValidationError):
        aggregate_demand_canvas(demand(), [demand()] * 3, x_max=240, y_max=2.2)
    with pytest.raises(ValidationError):
        aggregate_demand_canvas(demand(), x_max=60, y_max=2.2)


def test_axes_follow_the_model_and_the_arguments() -> None:
    wide = adas_canvas(model(), x_max=500, y_max=9)
    default = adas_canvas(model())
    bigger = adas_canvas(ASADModel(supply(), AggregateDemand(120, 45, 1)))

    assert (wide.spec.x_max, wide.spec.y_max) == (500, 9)
    assert bigger.spec.x_max > default.spec.x_max


def test_labels_come_from_the_locale_table() -> None:
    english = layers(adas_canvas(model()))["macro.adas.supply.label"]
    renamed = layers(adas_canvas(model(), labels={"adas.curve.supply": "S"}))

    assert english.text == "$AS$"  # type: ignore[attr-defined]
    assert renamed["macro.adas.supply.label"].text == "S"  # type: ignore[attr-defined]


def test_figures_render_and_save(tmp_path: Path) -> None:
    for index, canvas in enumerate(
        (
            adas_canvas(model()),
            adas_canvas(analyze_supply_shock(model(), scale=0.8), ambiguous_demand=True),
            aggregate_supply_canvas(supply()),
            aggregate_demand_canvas(demand(), [demand().with_money(30)], x_max=240, y_max=2.2),
        )
    ):
        target = tmp_path / f"figure{index}.svg"
        canvas.save(target)
        assert target.stat().st_size > 0
