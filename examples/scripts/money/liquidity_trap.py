"""Render the zero lower bound: money demand, and IS-LM with a flat LM curve."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import load_example, setup

from macro_viz.islm import ISLM, analyze_monetary_policy
from macro_viz.money import MoneyDemand, MoneyMarket, analyze_supply_shift
from macro_viz.visuals import islm_canvas, money_market_canvas


def main(argv: Sequence[str] | None = None) -> None:
    args, output = setup(__doc__ or "", argv)
    money = load_example(args.data, "money")
    trap = load_example(args.data, "liquidity_trap")
    suffix = args.suffix
    intercept, slope = money["liquidity_intercept"], money["liquidity_slope"]
    demand = MoneyDemand(
        money["nominal_income"],
        lambda rate: intercept - slope * rate,
        money["rate_max"],
        zero_bound=True,
    )
    market = MoneyMarket(demand, trap["supply_trap"])
    money_market_canvas(analyze_supply_shift(market, trap["supply_trap_after"])).save(
        output / f"money_zero_bound{suffix}"
    )

    data = load_example(args.data, "islm")
    model = ISLM(
        trap["autonomous_trap"],
        data["sensitivity"],
        trap["real_money_trap"],
        data["income_demand"],
        trap["rate_demand_zero"],
        data["multiplier"],
        zero_bound=True,
    )
    islm_canvas(
        analyze_monetary_policy(model, trap["real_money_trap_after"]), x_max=trap["x_max_trap"]
    ).save(output / f"islm_zero_bound{suffix}")


if __name__ == "__main__":
    main()
