"""Render aggregate supply and demand: the curves, their shifts, and a productivity shock."""

from __future__ import annotations

from collections.abc import Sequence

from common import load_example, setup

from macro_viz.adas import (
    AggregateDemand,
    AggregateSupply,
    ASADModel,
    analyze_demand_shock,
    analyze_supply_shock,
)
from macro_viz.visuals import adas_canvas, aggregate_demand_canvas, aggregate_supply_canvas


def main(argv: Sequence[str] | None = None) -> None:
    args, output = setup(__doc__ or "", argv)
    data = load_example(args.data, "adas")
    supply = AggregateSupply.linear(
        data["expected_price"], data["natural_output"], data["supply_slope"]
    )
    demand = AggregateDemand(data["autonomous"], data["money"], data["multiplier"])
    model = ASADModel(supply, demand)
    suffix = args.suffix

    aggregate_supply_canvas(supply).save(output / f"aggregate_supply{suffix}")
    aggregate_supply_canvas(
        supply, shifted=supply.with_expected_price(data["expected_price_after"])
    ).save(output / f"aggregate_supply_shift{suffix}")
    aggregate_demand_canvas(
        demand,
        [demand.with_autonomous(data["autonomous_after"]), demand.with_money(data["money_after"])],
        captions=[data["caption_government"], data["caption_money"]],
        x_max=data["demand_x_max"],
        y_max=data["demand_y_max"],
    ).save(output / f"aggregate_demand_shifts{suffix}")
    adas_canvas(model).save(output / f"adas_equilibrium{suffix}")
    adas_canvas(model, productivity=data["productivity"]).save(output / f"adas_employment{suffix}")
    productivity_shock = analyze_supply_shock(model, scale=data["productivity_scale"])
    adas_canvas(productivity_shock, ambiguous_demand=True).save(
        output / f"adas_productivity{suffix}"
    )
    demand_shock = analyze_demand_shock(model, autonomous=data["autonomous_shock"])
    adas_canvas(demand_shock).save(output / f"adas_demand_shock{suffix}")


if __name__ == "__main__":
    main()
