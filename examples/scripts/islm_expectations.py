"""Render IS-LM with expected inflation: the real rate below the nominal rate."""

from __future__ import annotations

from collections.abc import Sequence

from common import load_example, setup
from islm import build

from macro_viz.islm import ISLMExpectations
from macro_viz.visuals import islm_expectations_canvas


def main(argv: Sequence[str] | None = None) -> None:
    args, output = setup(__doc__ or "", argv)
    base = build(load_example(args.data, "islm"))
    data = load_example(args.data, "expectations")
    model = ISLMExpectations(base, data["expected_inflation"])
    suffix = args.suffix
    islm_expectations_canvas(model).save(output / f"islm_expected_inflation{suffix}")
    islm_expectations_canvas(model, after=model.with_real_money(data["real_money_after"])).save(
        output / f"islm_expected_inflation_money{suffix}"
    )


if __name__ == "__main__":
    main()
