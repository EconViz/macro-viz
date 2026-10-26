"""Render IS-LM: equilibrium, fiscal and monetary policy, crowding out, and LM shapes."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import load_example, setup
from model_common import build_islm

from macro_viz.islm import analyze_fiscal_policy, analyze_monetary_policy
from macro_viz.visuals import islm_canvas


def main(argv: Sequence[str] | None = None) -> None:
    args, output = setup(__doc__ or "", argv)
    data = load_example(args.data, "islm")
    model, suffix = build_islm(data), args.suffix
    islm_canvas(model).save(output / f"islm{suffix}")
    tax = analyze_fiscal_policy(model, data["autonomous_after"])
    islm_canvas(tax).save(output / f"islm_tax_increase{suffix}")
    money = analyze_monetary_policy(model, data["real_money_after"])
    islm_canvas(money).save(output / f"islm_monetary_expansion{suffix}")
    spending = analyze_fiscal_policy(model, 2 * data["autonomous"] - data["autonomous_after"])
    islm_canvas(spending, show_crowding=True).save(output / f"islm_crowding_out{suffix}")
    for name, key in (("flat", "rate_demand_flat"), ("steep", "rate_demand_steep")):
        shape = build_islm(data, data[key])
        shifted = analyze_fiscal_policy(shape, 2 * data["autonomous"] - data["autonomous_after"])
        islm_canvas(shifted).save(output / f"islm_{name}_lm{suffix}")


if __name__ == "__main__":
    main()
