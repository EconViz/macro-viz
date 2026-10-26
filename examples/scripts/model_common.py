"""Models several example topics build from the same ``examples.toml`` tables."""

from __future__ import annotations

from macro_viz.growth import Solow
from macro_viz.islm import ISLM


def build_islm(data: dict, rate_demand: float | None = None) -> ISLM:  # type: ignore[type-arg]
    return ISLM(
        data["autonomous"],
        data["sensitivity"],
        data["real_money"],
        data["income_demand"],
        data["rate_demand"] if rate_demand is None else rate_demand,
        data["multiplier"],
    )


def build_solow(data: dict, **changes: float) -> Solow:  # type: ignore[type-arg]
    values = {
        "alpha": data["alpha"],
        "saving": data["saving"],
        "depreciation": data["depreciation"],
        "population_growth": data["population_growth"],
        "tech_growth": data["tech_growth"],
        "productivity": data["productivity"],
    }
    values.update(changes)
    return Solow.cobb_douglas(**values)
