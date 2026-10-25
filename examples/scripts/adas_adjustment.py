"""Render the medium-run adjustment of AS-AD after expectations, money, deficit, and oil shocks."""

from __future__ import annotations

from collections.abc import Sequence

from common import load_example, setup

from macro_viz.adas import (
    AggregateDemand,
    AggregateSupply,
    ASADModel,
    analyze_adjustment,
    analyze_demand_shock,
    analyze_supply_shock,
)
from macro_viz.visuals import adas_adjustment_canvas


def main(argv: Sequence[str] | None = None) -> None:
    args, output = setup(__doc__ or "", argv)
    data = load_example(args.data, "adas")
    move = load_example(args.data, "adjustment")
    supply = AggregateSupply.linear(
        data["expected_price"], data["natural_output"], data["supply_slope"]
    )
    natural = ASADModel(supply, AggregateDemand(55, data["money"], data["multiplier"]))
    boom = ASADModel(supply, AggregateDemand(data["autonomous"], data["money"], 1))
    suffix, rounds = args.suffix, move["rounds_expectations"]

    adas_adjustment_canvas(analyze_adjustment(boom, rounds)).save(
        output / f"adjustment_expectations{suffix}"
    )
    money = analyze_demand_shock(natural, money=move["money_after"])
    adas_adjustment_canvas(analyze_adjustment(money)).save(output / f"adjustment_money{suffix}")
    deficit = analyze_demand_shock(natural, autonomous=move["autonomous_after_deficit"])
    adas_adjustment_canvas(analyze_adjustment(deficit)).save(output / f"adjustment_deficit{suffix}")
    oil = analyze_supply_shock(natural, scale=move["cost_scale"])
    adas_adjustment_canvas(analyze_adjustment(oil)).save(output / f"adjustment_oil{suffix}")


if __name__ == "__main__":
    main()
