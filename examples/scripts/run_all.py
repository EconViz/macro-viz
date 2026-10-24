"""Run every P0 accounts and business-cycle example."""

from __future__ import annotations

from business_cycle import main as business_cycle_main
from common import clear_images
from gdp_and_prices import main as gdp_and_prices_main
from gdp_components import main as gdp_components_main
from labor_market import main as labor_market_main


def main() -> None:
    clear_images()
    gdp_components_main()
    gdp_and_prices_main()
    labor_market_main()
    business_cycle_main()


if __name__ == "__main__":
    main()
