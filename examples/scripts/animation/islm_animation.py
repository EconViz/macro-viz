"""Animate a monetary expansion: LM shifts right and the interest rate falls."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import load_example, setup
from model_common import build_islm

from macro_viz import ValidationError
from macro_viz.animation import linear_values, save_gif, save_svg
from macro_viz.islm import analyze_monetary_policy
from macro_viz.visuals import islm_canvas
from macro_viz.visuals._theory import EXTENT


def main(argv: Sequence[str] | None = None) -> None:
    args, output = setup(__doc__ or "", argv)
    data = load_example(args.data, "islm")
    model = build_islm(data)
    final = analyze_monetary_policy(model, data["real_money_after"]).after
    x_max = EXTENT * max(final.output, model.equilibrium().output)
    rates = 2.0 * model.equilibrium().rate

    def builder(real_money: float):  # type: ignore[no-untyped-def]
        shift = analyze_monetary_policy(model, real_money)
        return islm_canvas(shift, x_max=x_max, rate_max=rates)

    start, stop, count = data["real_money"], data["real_money_after"], data["frames"]
    values = linear_values(start + (stop - start) / count, stop, count)
    try:
        save_svg(builder, values, output / "islm_animation.svg", step_seconds=data["step_seconds"])
    except ValidationError as error:
        print(f"skipped the animated SVG: {error}")
    try:
        save_gif(builder, values, output / "islm_animation.gif", fps=data["fps"], dpi=data["dpi"])
    except ImportError:
        print("KineticKit's raster extra is not installed; skipped the GIF")


if __name__ == "__main__":
    main()
