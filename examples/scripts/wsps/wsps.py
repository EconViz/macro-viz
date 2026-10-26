"""Render wage setting and price setting: the natural rate and what shifts it."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import load_example, setup

from macro_viz.labor import WagePriceSetting, compare
from macro_viz.visuals import wsps_canvas


def main(argv: Sequence[str] | None = None) -> None:
    args, output = setup(__doc__ or "", argv)
    data = load_example(args.data, "wsps")
    model = WagePriceSetting(data["level"], data["slope"], data["benefits"], data["markup"])
    suffix = args.suffix
    wsps_canvas(model).save(output / f"wsps{suffix}")
    wsps_canvas(compare(model, model.with_benefits(data["benefits_after"]))).save(
        output / f"wsps_benefits{suffix}"
    )
    wsps_canvas(compare(model, model.with_markup(data["markup_after"]))).save(
        output / f"wsps_markup{suffix}"
    )
    common = model.with_productivity(data["productivity_after"], data["productivity_after"])
    wsps_canvas(compare(model, common)).save(output / f"wsps_productivity{suffix}")
    split = model.with_productivity(data["ws_after"], data["ps_after"])
    wsps_canvas(compare(model, split)).save(output / f"wsps_productivity_split{suffix}")
    wsps_canvas(model, labor_force=data["labor_force"]).save(output / f"wsps_employment{suffix}")


if __name__ == "__main__":
    main()
