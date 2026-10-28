"""The supply and demand curves inside a plot."""

from __future__ import annotations

from collections.abc import Sequence

from macro_viz.adas.models import AggregateDemand, AggregateSupply, ASADModel
from macro_viz.adas.visuals._preset import DEMAND_FLOOR_SHARE
from macro_viz.core.errors import ValidationError
from macro_viz.visuals._theory import (
    HEADROOM,
    sample,
    trim,
)


def supply_curve(
    supply: AggregateSupply, x_max: float, y_max: float, samples: int
) -> list[tuple[float, float]]:
    """The aggregate supply curve inside the plot."""
    return trim(sample(supply.price, 0.0, x_max, samples), x_max, y_max)


def demand_curve(
    demand: AggregateDemand, x_max: float, y_max: float, samples: int
) -> list[tuple[float, float]]:
    """The aggregate demand curve from the top of the plot to the right edge."""
    top = HEADROOM * y_max
    start = demand.autonomous + demand.multiplier * demand.money / top
    stop = min(HEADROOM * x_max, demand.output(DEMAND_FLOOR_SHARE * y_max))
    if start >= stop:
        raise ValidationError("the demand curve does not enter the plot; widen the axes")
    return sample(demand.price, start, stop, samples)


def _scale(
    models: Sequence[ASADModel], x_max: float | None, y_max: float | None, extent: float
) -> tuple[float, float]:
    outputs, prices = [], []
    for model in models:
        equilibrium = model.equilibrium()
        outputs += [equilibrium.output, equilibrium.natural_output]
        prices += [equilibrium.price, equilibrium.expected_price]
    return (
        x_max if x_max is not None else extent * max(outputs),
        y_max if y_max is not None else extent * max(prices),
    )
