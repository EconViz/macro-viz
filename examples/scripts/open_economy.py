"""Render the open-economy goods market: equilibrium, fiscal expansion, and foreign demand."""

from __future__ import annotations

from collections.abc import Sequence

from common import load_example, setup

from macro_viz.keynesian import ConsumptionFunction, KeynesianCross
from macro_viz.open_economy import OpenEconomy, compare
from macro_viz.visuals import open_goods_canvas


def main(argv: Sequence[str] | None = None) -> None:
    args, output = setup(__doc__ or "", argv)
    closed = load_example(args.data, "keynesian")
    data = load_example(args.data, "open_economy")
    domestic = KeynesianCross(
        ConsumptionFunction(closed["autonomous_consumption"], closed["propensity"]),
        closed["investment"],
        closed["government"],
        closed["taxes"],
    )
    model = OpenEconomy(domestic, data["exports"], data["import_propensity"])
    suffix = args.suffix
    open_goods_canvas(model).save(output / f"open_goods{suffix}")
    open_goods_canvas(compare(model, model.with_government(data["government_after"]))).save(
        output / f"open_fiscal_expansion{suffix}"
    )
    open_goods_canvas(compare(model, model.with_exports(data["exports_after"]))).save(
        output / f"open_foreign_demand{suffix}"
    )


if __name__ == "__main__":
    main()
