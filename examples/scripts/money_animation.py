"""Animate an increase in the money supply: the supply line moves and the interest rate falls."""

from __future__ import annotations

from collections.abc import Sequence

from common import load_example, setup

from macro_viz import ValidationError
from macro_viz.animation import linear_values, save_gif, save_svg
from macro_viz.money import MoneyDemand, MoneyMarket, analyze_supply_shift
from macro_viz.visuals import money_market_canvas
from macro_viz.visuals.money import MONEY_EXTENT


def main(argv: Sequence[str] | None = None) -> None:
    args, output = setup(__doc__ or "", argv)
    data = load_example(args.data, "money")
    motion = load_example(args.data, "money_animation")
    intercept, slope = data["liquidity_intercept"], data["liquidity_slope"]
    demand = MoneyDemand(
        data["nominal_income"], lambda rate: intercept - slope * rate, data["rate_max"]
    )
    market = MoneyMarket(demand, data["supply"])
    limit = MONEY_EXTENT * max(demand.quantity(0.0), data["supply_after"])

    def builder(supply: float):  # type: ignore[no-untyped-def]
        return money_market_canvas(analyze_supply_shift(market, supply), x_max=limit)

    start, stop, count = data["supply"], data["supply_after"], motion["frames"]
    values = linear_values(start + (stop - start) / count, stop, count)
    try:
        save_svg(
            builder,
            values,
            output / "money_supply_animation.svg",
            step_seconds=motion["step_seconds"],
        )
    except ValidationError as error:
        print(f"skipped the animated SVG: {error}")
    try:
        save_gif(
            builder,
            values,
            output / "money_supply_animation.gif",
            fps=motion["fps"],
            dpi=motion["dpi"],
        )
    except ImportError:
        print("KineticKit's raster extra is not installed; skipped the GIF")


if __name__ == "__main__":
    main()
