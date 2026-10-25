"""Render the five-panel diagram: IS-LM above AD-AS, with the labour market and production."""

from __future__ import annotations

from collections.abc import Sequence

from common import load_example, setup
from panels_common import capital, expenditure, hidden

from macro_viz.panels import Mode
from macro_viz.visuals import five_panel_canvas


def main(argv: Sequence[str] | None = None) -> None:
    args, output = setup(__doc__ or "", argv)
    data = load_example(args.data, "panels")
    suffix = args.suffix
    common = {"extent": data["drawing"]["extent"], "width": data["drawing"]["width"]}

    table = data["capital"]
    five_panel_canvas(
        capital(data),
        hide_ticks=hidden(data, "capital"),
        labels={"panels.curve.sras": table["sras_label"]},
        **common,
    ).save(output / f"five_panel_capital{suffix}")

    five_panel_canvas(
        expenditure(data),
        mode=Mode.DERIVED,
        lras=True,
        shifted_sras=data["expenditure"]["shifted_sras"],
        hide_ticks=hidden(data, "expenditure"),
        **common,
    ).save(output / f"five_panel_expenditure{suffix}")


if __name__ == "__main__":
    main()
