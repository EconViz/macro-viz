"""Render the consumption function, the Keynesian cross, and the multiplier."""

from __future__ import annotations

from collections.abc import Sequence

from common import load_example, setup

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


def main(argv: Sequence[str] | None = None) -> None:
    args, output = setup(__doc__ or "", argv)
    data = load_example(args.data, "keynesian")
    function = ConsumptionFunction(data["autonomous_consumption"], data["propensity"])
    model = KeynesianCross(function, data["investment"], data["government"], data["taxes"])
    suffix = args.suffix

    consumption_function_canvas(function, data["income_max"]).save(
        output / f"consumption_function{suffix}"
    )
    keynesian_cross_canvas(model).save(output / f"keynesian_cross{suffix}")
    shift = analyze_autonomous_shift(model, data["autonomous_change"])
    multiplier_canvas(shift, rounds=data["rounds"]).save(output / f"multiplier{suffix}")

    curved = CurvedDemand(
        lambda y: data["curve_intercept"] + data["curve_slope"] * y + data["curve_bend"] * y**2,
        0.0,
        data["curve_upper"],
    )
    keynesian_cross_canvas(curved).save(output / f"keynesian_cross_curved{suffix}")


if __name__ == "__main__":
    main()
