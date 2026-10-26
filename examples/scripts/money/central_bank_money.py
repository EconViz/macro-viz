"""Render the market for central-bank money and the effect of an open market purchase."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import load_example, setup

from macro_viz.money import (
    MoneyDemand,
    MoneyMarket,
    MoneyMultiplier,
    analyze_supply_shift,
)
from macro_viz.visuals import central_bank_money_canvas


def main(argv: Sequence[str] | None = None) -> None:
    args, output = setup(__doc__ or "", argv)
    money = load_example(args.data, "money")
    ratios = load_example(args.data, "central_bank_money")
    multiplier = MoneyMultiplier(ratios["currency_ratio"], ratios["reserve_ratio"])
    intercept, slope = money["liquidity_intercept"], money["liquidity_slope"]
    demand = MoneyDemand(
        money["nominal_income"], lambda r: intercept - slope * r, money["rate_max"]
    )
    market = MoneyMarket(demand, money["supply"])
    central_bank_money_canvas(multiplier, market).save(output / f"central_bank_money{args.suffix}")
    central_bank_money_canvas(multiplier, analyze_supply_shift(market, money["supply_after"])).save(
        output / f"central_bank_money_purchase{args.suffix}"
    )


if __name__ == "__main__":
    main()
