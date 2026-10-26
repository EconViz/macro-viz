"""Render the Solow model: production function, steady state, golden rule, and time paths."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import load_example, setup
from model_common import build_solow

from macro_viz.growth import analyze_change, simulate
from macro_viz.visuals import (
    golden_rule_canvas,
    production_function_canvas,
    solow_canvas,
    solow_growth_rate_canvas,
    solow_level_path_canvas,
    solow_log_path_canvas,
)


def main(argv: Sequence[str] | None = None) -> None:
    args, output = setup(__doc__ or "", argv)
    data = load_example(args.data, "solow")
    model, suffix = build_solow(data), args.suffix

    production_function_canvas(model, points=data["points"]).save(
        output / f"production_function{suffix}"
    )
    production_function_canvas(
        model, shifted=build_solow(data, productivity=data["productivity_after"])
    ).save(output / f"production_function_shift{suffix}")
    solow_canvas(model).save(output / f"solow{suffix}")
    saving_up = build_solow(data, saving=data["saving_after"])
    solow_canvas(analyze_change(model, saving_up)).save(output / f"solow_saving_increase{suffix}")
    solow_canvas(
        analyze_change(model, build_solow(data, population_growth=data["population_after"])),
        effective=True,
    ).save(output / f"solow_population_growth{suffix}")
    golden_rule_canvas(model).save(output / f"golden_rule{suffix}")

    technology = build_solow(data, tech_growth=data["tech_after"])
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
