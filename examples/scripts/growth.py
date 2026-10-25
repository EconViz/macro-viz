"""Render the Solow model: production function, steady state, golden rule, and time paths."""

from __future__ import annotations

from collections.abc import Sequence

from common import load_example, setup

from macro_viz.growth import Solow, analyze_change, simulate
from macro_viz.visuals import (
    golden_rule_canvas,
    production_function_canvas,
    solow_canvas,
    solow_growth_rate_canvas,
    solow_level_path_canvas,
    solow_log_path_canvas,
)


def build(data: dict, **changes: float) -> Solow:  # type: ignore[type-arg]
    values = {
        "alpha": data["alpha"],
        "saving": data["saving"],
        "depreciation": data["depreciation"],
        "population_growth": data["population_growth"],
        "tech_growth": data["tech_growth"],
        "productivity": data["productivity"],
    }
    values.update(changes)
    return Solow.cobb_douglas(**values)


def main(argv: Sequence[str] | None = None) -> None:
    args, output = setup(__doc__ or "", argv)
    data = load_example(args.data, "solow")
    model, suffix = build(data), args.suffix

    production_function_canvas(model, points=data["points"]).save(
        output / f"production_function{suffix}"
    )
    production_function_canvas(
        model, shifted=build(data, productivity=data["productivity_after"])
    ).save(output / f"production_function_shift{suffix}")
    solow_canvas(model).save(output / f"solow{suffix}")
    saving_up = build(data, saving=data["saving_after"])
    solow_canvas(analyze_change(model, saving_up)).save(output / f"solow_saving_increase{suffix}")
    solow_canvas(
        analyze_change(model, build(data, population_growth=data["population_after"])),
        effective=True,
    ).save(output / f"solow_population_growth{suffix}")
    golden_rule_canvas(model).save(output / f"golden_rule{suffix}")

    technology = build(data, tech_growth=data["tech_after"])
    path = simulate(
        technology,
        technology.with_saving(data["saving_after"]),
        periods=data["periods"],
        change_period=data["change_period"],
    )
    solow_level_path_canvas(path).save(output / f"solow_level_path{suffix}")
    solow_log_path_canvas(path).save(output / f"solow_log_path{suffix}")
    solow_growth_rate_canvas(path).save(output / f"solow_growth_rate{suffix}")


if __name__ == "__main__":
    main()
