"""Render open-economy AS-AD: slow adjustment under a fixed rate, and a devaluation."""

from __future__ import annotations

from collections.abc import Sequence

from common import load_example, setup

from macro_viz.adas import (
    AggregateDemand,
    AggregateSupply,
    ASADModel,
    analyze_adjustment,
)
from macro_viz.open_economy import analyze_devaluation
from macro_viz.visuals import adas_adjustment_canvas, adas_canvas


def main(argv: Sequence[str] | None = None) -> None:
    args, output = setup(__doc__ or "", argv)
    adas = load_example(args.data, "adas")
    data = load_example(args.data, "open_asad")
    supply = AggregateSupply.linear(
        adas["expected_price"], adas["natural_output"], adas["supply_slope"]
    )
    slump = ASADModel(
        supply, AggregateDemand(data["autonomous_slump"], adas["money"], adas["multiplier"])
    )
    suffix = args.suffix
    adas_canvas(slump).save(output / f"open_asad_below_natural{suffix}")
    adas_adjustment_canvas(analyze_adjustment(slump, rounds=0)).save(
        output / f"open_asad_fixed_rate{suffix}"
    )
    shift = analyze_devaluation(slump, data["devaluation"], exchange_effect=data["exchange_effect"])
    adas_canvas(shift).save(output / f"open_asad_devaluation{suffix}")


if __name__ == "__main__":
    main()
