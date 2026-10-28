"""The 45-degree line and demand curve shared by the goods-market figures."""

from __future__ import annotations

from mosaickit import Layer, PathLayer, TextLayer

from macro_viz.core.i18n import Labels
from macro_viz.keynesian.models import (
    GoodsMarket,
)
from macro_viz.keynesian.visuals._preset import LABEL_GAP
from macro_viz.visuals._theory import (
    curve,
    sample,
    trim,
)


def _base_layers(
    model: GoodsMarket,
    x_max: float,
    text: Labels,
    samples: int,
    *,
    demand_id: str = "macro.keynesian.demand",
    demand_label_id: str = "keynesian.curve.demand",
    role: str = "macro.curve.primary",
) -> list[Layer]:
    """The 45-degree production line and the demand curve of ``model``."""
    production = trim([(0.0, 0.0), (x_max, x_max)], x_max, x_max)
    layers: list[Layer] = [
        PathLayer(
            tuple(production),
            id="macro.keynesian.production",
            role="macro.line45",
            clip=False,
            z_index=2,
        ),
        TextLayer(
            production[-1],
            text("keynesian.mark.degrees"),
            id="macro.keynesian.production.label",
            role="macro.annotation",
            anchor="bottom-left",
            offset=(LABEL_GAP, 0),
        ),
    ]
    demand = trim(sample(model.demand, 0.0, x_max, samples), x_max, x_max)
    layers += curve(demand, layer_id=demand_id, role=role, label=text(demand_label_id))
    return layers
