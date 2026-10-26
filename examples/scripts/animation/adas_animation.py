"""Animate a rise in government spending: AD shifts right and the economy moves along AS."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import load_example, setup

from macro_viz import ValidationError
from macro_viz.adas import AggregateDemand, AggregateSupply, ASADModel, analyze_demand_shock
from macro_viz.animation import linear_values, save_gif, save_svg
from macro_viz.visuals import adas_canvas
from macro_viz.visuals._theory import EXTENT


def main(argv: Sequence[str] | None = None) -> None:
    args, output = setup(__doc__ or "", argv)
    data = load_example(args.data, "adas")
    motion = load_example(args.data, "adas_animation")
    supply = AggregateSupply.linear(
        data["expected_price"], data["natural_output"], data["supply_slope"]
    )
    model = ASADModel(
        supply, AggregateDemand(data["autonomous"], data["money"], data["multiplier"])
    )
    final = analyze_demand_shock(model, autonomous=data["autonomous_after"]).after
    x_max = EXTENT * max(final.output, final.natural_output)
    y_max = EXTENT * max(final.price, final.expected_price)

    def builder(autonomous: float):  # type: ignore[no-untyped-def]
        shock = analyze_demand_shock(model, autonomous=autonomous)
        return adas_canvas(shock, x_max=x_max, y_max=y_max)

    start, stop, count = data["autonomous"], data["autonomous_after"], motion["frames"]
    values = linear_values(start + (stop - start) / count, stop, count)
    try:
        save_svg(
            builder, values, output / "adas_animation.svg", step_seconds=motion["step_seconds"]
        )
    except ValidationError as error:
        print(f"skipped the animated SVG: {error}")
    try:
        save_gif(
            builder, values, output / "adas_animation.gif", fps=motion["fps"], dpi=motion["dpi"]
        )
    except ImportError:
        print("KineticKit's raster extra is not installed; skipped the GIF")


if __name__ == "__main__":
    main()
