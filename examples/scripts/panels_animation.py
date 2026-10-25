"""Animate the linked panels: the steps A, B, C of a scenario appear one after another."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from common import load_example, setup
from panels_common import capital, hidden, money_illusion

from macro_viz.animation import linear_values, save_gif
from macro_viz.panels import Scenario
from macro_viz.visuals import five_panel_canvas, four_panel_canvas


def reveal(
    draw: Callable[..., object], scenario: Scenario, **options: object
) -> Callable[[float], object]:
    """A builder that marks the first ``round(value)`` steps of ``scenario``.

    Every range comes from the whole scenario, so the axes stay put between frames.
    """
    labels = [step.label for step in scenario.steps]

    def builder(value: float) -> object:
        return draw(scenario, steps=labels[: round(value)], **options)

    return builder


def main(argv: Sequence[str] | None = None) -> None:
    args, output = setup(__doc__ or "", argv)
    data = load_example(args.data, "panels")
    motion = load_example(args.data, "panels_animation")
    common = {"extent": data["drawing"]["extent"], "width": data["drawing"]["width"]}
    suffix = args.suffix

    steps = capital(data)
    values = linear_values(1, len(steps.steps), len(steps.steps))
    save_gif(
        reveal(  # type: ignore[arg-type]
            five_panel_canvas,
            steps,
            hide_ticks=hidden(data, "capital"),
            labels={"panels.curve.sras": data["capital"]["sras_label"]},
            **common,
        ),
        values,
        output / f"five_panel_capital_animation{suffix}".replace(".svg", ".gif"),
        fps=motion["fps"],
        dpi=motion["dpi"],
    )

    illusion = money_illusion(data)
    table = data["money_illusion"]
    values = linear_values(1, len(illusion.steps), len(illusion.steps))
    save_gif(
        reveal(  # type: ignore[arg-type]
            four_panel_canvas,
            illusion,
            lras=table["lras"],
            ad=False,
            shifted_sras=table["shifted_sras"],
            shift_arrows_on=False,
            hide_ticks=hidden(data, "money_illusion"),
            **common,
        ),
        values,
        output / f"four_panel_money_lras_animation{suffix}".replace(".svg", ".gif"),
        fps=motion["fps"],
        dpi=motion["dpi"],
    )


if __name__ == "__main__":
    main()
