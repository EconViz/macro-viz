"""Render the IS, LM, AD, and AS derivations plus standalone IS-LM and AD-AS."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import load_example, setup
from panels_common import economy

from macro_viz.adas import AggregateDemand, AggregateSupply, ASADModel
from macro_viz.islm import ISLM
from macro_viz.keynesian import ConsumptionFunction, KeynesianCross
from macro_viz.money import MoneyDemand, MoneyMarket
from macro_viz.transmission import ADDerivation, ASDerivation, ISDerivation, LMDerivation
from macro_viz.visuals import (
    ad_derivation_canvas,
    adas_canvas,
    as_derivation_canvas,
    is_derivation_canvas,
    islm_canvas,
    lm_derivation_canvas,
)


def main(argv: Sequence[str] | None = None) -> None:
    args, output = setup(__doc__ or "", argv)
    transmission = load_example(args.data, "transmission")
    keynesian = load_example(args.data, "keynesian")
    money = load_example(args.data, "money")
    islm_data = load_example(args.data, "islm")
    adas_data = load_example(args.data, "adas")
    panels = load_example(args.data, "panels")
    suffix = args.suffix

    goods = KeynesianCross(
        ConsumptionFunction(
            transmission["is_autonomous_consumption"], transmission["is_propensity"]
        ),
        transmission["investment_at_zero"],
        transmission["is_government"],
        keynesian["taxes"],
    )
    money_market = MoneyMarket(
        MoneyDemand(
            money["nominal_income"],
            lambda rate: money["liquidity_intercept"] - money["liquidity_slope"] * rate,
            money["rate_max"],
        ),
        money["supply"],
    )
    islm = ISLM(
        islm_data["autonomous"],
        islm_data["sensitivity"],
        islm_data["real_money"],
        islm_data["income_demand"],
        islm_data["rate_demand"],
        islm_data["multiplier"],
    )
    adas = ASADModel(
        AggregateSupply.linear(
            adas_data["expected_price"],
            adas_data["natural_output"],
            adas_data["supply_slope"],
        ),
        AggregateDemand(adas_data["autonomous"], adas_data["money"], adas_data["multiplier"]),
    )

    is_derivation_canvas(
        ISDerivation(
            goods,
            transmission["investment_sensitivity"],
            tuple(transmission["is_rates"]),
        )
    ).save(output / f"is_derivation{suffix}")
    lm_derivation_canvas(LMDerivation(money_market, tuple(transmission["lm_outputs"]))).save(
        output / f"lm_derivation{suffix}"
    )
    ad_derivation_canvas(
        ADDerivation(
            ISLM(
                transmission["ad_autonomous"],
                transmission["ad_sensitivity"],
                transmission["nominal_money"],
                islm_data["income_demand"],
                transmission["ad_real_money_demand"],
                islm_data["multiplier"],
            ),
            transmission["nominal_money"],
            tuple(transmission["ad_prices"]),
        )
    ).save(output / f"ad_derivation{suffix}")
    as_derivation_canvas(ASDerivation(economy(panels), tuple(transmission["as_prices"]))).save(
        output / f"as_derivation{suffix}"
    )
    islm_canvas(islm).save(output / f"islm_standalone{suffix}")
    adas_canvas(adas).save(output / f"adas_standalone{suffix}")


if __name__ == "__main__":
    main()
