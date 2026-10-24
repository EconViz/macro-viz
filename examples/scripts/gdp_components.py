"""Render the GDP expenditure identity."""

from __future__ import annotations

from common import prepare_manual_output

from macro_viz.accounts import GDPComponents, analyze_gdp_components
from macro_viz.visuals import gdp_decomposition_canvas


def main() -> None:
    output = prepare_manual_output()
    result = analyze_gdp_components(
        GDPComponents(
            consumption=620,
            investment=170,
            government=230,
            net_exports=-20,
            unit="billions USD",
        )
    )
    gdp_decomposition_canvas(result, title="GDP expenditure components").save(
        output / "gdp_components.png"
    )


if __name__ == "__main__":
    main()
