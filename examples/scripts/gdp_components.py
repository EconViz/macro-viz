"""Render the GDP expenditure identity."""

from __future__ import annotations

from collections.abc import Sequence

from common import load_example, setup

from macro_viz.accounts import GDPComponents, analyze_gdp_components
from macro_viz.visuals import gdp_decomposition_canvas


def main(argv: Sequence[str] | None = None) -> None:
    args, output = setup(__doc__ or "", argv)
    data = load_example(args.data, "gdp_components")
    result = analyze_gdp_components(
        GDPComponents(
            consumption=data["consumption"],
            investment=data["investment"],
            government=data["government"],
            net_exports=data["net_exports"],
            unit=data["unit"],
        )
    )
    gdp_decomposition_canvas(result, title=data["title"]).save(
        output / f"gdp_components{args.suffix}"
    )


if __name__ == "__main__":
    main()
