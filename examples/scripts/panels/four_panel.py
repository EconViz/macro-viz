"""Render the four-panel diagram: labour market, AD-AS, production function, 45-degree line."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import load_example, setup
from panels_common import hidden, money_illusion, money_sas

from macro_viz.visuals import four_panel_canvas


def main(argv: Sequence[str] | None = None) -> None:
    args, output = setup(__doc__ or "", argv)
    data = load_example(args.data, "panels")
    suffix = args.suffix
    common = {"extent": data["drawing"]["extent"], "width": data["drawing"]["width"]}

    sticky = data["money_sas"]
    four_panel_canvas(money_sas(data), lras=sticky["lras"], steps=sticky["steps"], **common).save(
        output / f"four_panel_money_sras{suffix}"
    )

    illusion = data["money_illusion"]
    four_panel_canvas(
        money_illusion(data),
        lras=illusion["lras"],
        ad=False,
        shifted_sras=illusion["shifted_sras"],
        shift_arrows_on=False,
        steps=illusion["steps"],
        hide_ticks=hidden(data, "money_illusion"),
        **common,
    ).save(output / f"four_panel_money_lras{suffix}")


if __name__ == "__main__":
    main()
