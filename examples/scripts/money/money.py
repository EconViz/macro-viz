"""Render money demand, the money market, and the effects of income and money supply."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import load_example, setup

from macro_viz.money import MoneyDemand, MoneyMarket, analyze_income_shift, analyze_supply_shift
from macro_viz.visuals import money_demand_canvas, money_market_canvas


def main(argv: Sequence[str] | None = None) -> None:
    args, output = setup(__doc__ or "", argv)
    data = load_example(args.data, "money")
    intercept, slope = data["liquidity_intercept"], data["liquidity_slope"]
    demand = MoneyDemand(
        data["nominal_income"], lambda rate: intercept - slope * rate, data["rate_max"]
    )
    market = MoneyMarket(demand, data["supply"])
    income_shift = analyze_income_shift(market, data["nominal_income_after"])
    supply_shift = analyze_supply_shift(market, data["supply_after"])
    suffix = args.suffix

    money_demand_canvas(income_shift).save(output / f"money_demand{suffix}")
    money_market_canvas(market).save(output / f"money_market{suffix}")
    money_market_canvas(income_shift).save(output / f"money_income_shift{suffix}")
    money_market_canvas(supply_shift).save(output / f"money_supply_shift{suffix}")


if __name__ == "__main__":
    main()
