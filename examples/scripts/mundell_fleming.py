"""Render interest parity and floating-rate IS-LM after a fiscal and a monetary change."""

from __future__ import annotations

from collections.abc import Sequence

from common import load_example, setup
from islm import build

from macro_viz.open_economy import InterestParity, OpenISLM
from macro_viz.visuals import interest_parity_canvas, open_islm_canvas


def main(argv: Sequence[str] | None = None) -> None:
    args, output = setup(__doc__ or "", argv)
    data = load_example(args.data, "mundell_fleming")
    parity = InterestParity(data["foreign_rate"], data["expected_rate"], data["parity_slope"])
    model = OpenISLM(build(load_example(args.data, "islm")), parity, data["exchange_effect"])
    suffix = args.suffix
    interest_parity_canvas(parity).save(output / f"interest_parity{suffix}")
    open_islm_canvas(model).save(output / f"open_islm{suffix}")
    open_islm_canvas(model, fiscal=data["fiscal_after"]).save(output / f"open_islm_fiscal{suffix}")
    open_islm_canvas(model, money=data["money_after"]).save(output / f"open_islm_money{suffix}")


if __name__ == "__main__":
    main()
