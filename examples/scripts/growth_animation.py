"""Animate a rise in the saving rate on the Solow diagram."""

from __future__ import annotations

from collections.abc import Sequence

from common import load_example, setup
from growth import build

from macro_viz import ValidationError
from macro_viz.animation import linear_values, save_gif, save_svg
from macro_viz.growth import analyze_change
from macro_viz.visuals import solow_canvas
from macro_viz.visuals.growth import SOLOW_EXTENT


def main(argv: Sequence[str] | None = None) -> None:
    args, output = setup(__doc__ or "", argv)
    data = load_example(args.data, "solow")
    model = build(data)
    final = build(data, saving=data["saving_after"])
    k_max = SOLOW_EXTENT * final.steady_state()
    y_max = max(model.output(k_max), final.output(k_max)) / 0.92

    def builder(saving: float):  # type: ignore[no-untyped-def]
        change = analyze_change(model, build(data, saving=saving))
        return solow_canvas(change, k_max=k_max, y_max=y_max)

    start, stop, count = data["saving"], data["saving_after"], data["frames"]
    values = linear_values(start + (stop - start) / count, stop, count)
    try:
        save_svg(builder, values, output / "solow_animation.svg", step_seconds=data["step_seconds"])
    except ValidationError as error:
        print(f"skipped the animated SVG: {error}")
    try:
        save_gif(builder, values, output / "solow_animation.gif", fps=data["fps"], dpi=data["dpi"])
    except ImportError:
        print("KineticKit's raster extra is not installed; skipped the GIF")


if __name__ == "__main__":
    main()
