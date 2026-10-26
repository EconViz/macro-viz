"""Animate a rise in autonomous spending: the demand line climbs toward its new position."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import load_example, setup

from macro_viz import ValidationError
from macro_viz.animation import linear_values, save_gif, save_svg
from macro_viz.keynesian import (
    ConsumptionFunction,
    KeynesianCross,
    analyze_autonomous_shift,
)
from macro_viz.visuals import multiplier_canvas
from macro_viz.visuals._theory import EXTENT


def main(argv: Sequence[str] | None = None) -> None:
    args, output = setup(__doc__ or "", argv)
    data = load_example(args.data, "keynesian")
    motion = load_example(args.data, "keynesian_animation")
    function = ConsumptionFunction(data["autonomous_consumption"], data["propensity"])
    model = KeynesianCross(function, data["investment"], data["government"], data["taxes"])
    change = data["autonomous_change"]
    limit = EXTENT * analyze_autonomous_shift(model, change).post.equilibrium().output

    def builder(amount: float):  # type: ignore[no-untyped-def]
        shift = analyze_autonomous_shift(model, amount)
        return multiplier_canvas(shift, show_path=False, x_max=limit)

    values = linear_values(change / 2, change, motion["frames"])
    try:
        save_svg(
            builder,
            values,
            output / "multiplier_animation.svg",
            step_seconds=motion["step_seconds"],
        )
    except ValidationError as error:
        print(f"skipped the animated SVG: {error}")
    try:
        save_gif(
            builder,
            values,
            output / "multiplier_animation.gif",
            fps=motion["fps"],
            dpi=motion["dpi"],
        )
    except ImportError:
        print("KineticKit's raster extra is not installed; skipped the GIF")


if __name__ == "__main__":
    main()
