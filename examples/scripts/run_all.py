"""Run every example."""

from __future__ import annotations

from collections.abc import Sequence

from business_cycle import main as business_cycle_main
from common import clear_images, parse_arguments
from gdp_and_prices import main as gdp_and_prices_main
from gdp_components import main as gdp_components_main
from keynesian import main as keynesian_main
from keynesian_animation import main as keynesian_animation_main
from labor_market import main as labor_market_main


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_arguments(__doc__ or "", argv)
    args.output.mkdir(parents=True, exist_ok=True)
    clear_images(args.output)
    for example in (
        gdp_components_main,
        gdp_and_prices_main,
        labor_market_main,
        business_cycle_main,
        keynesian_main,
        keynesian_animation_main,
    ):
        example(argv)


if __name__ == "__main__":
    main()
