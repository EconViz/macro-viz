"""Open-economy AS-AD: adjustment under a fixed exchange rate and a devaluation.

The exchange rate acts on aggregate demand only: a devaluation raises net exports at every price
level, shifting AD right by ``exchange_effect`` times the devaluation, while aggregate supply is
unchanged in the short run. Under a fixed rate the economy then adjusts as in the closed model
(expected prices follow actual prices), which ``analyze_adjustment`` lists.
"""

from __future__ import annotations

from macro_viz.adas.analysis import ASADShift, analyze_demand_shock
from macro_viz.adas.models import ASADModel
from macro_viz.errors import ValidationError


def analyze_devaluation(
    model: ASADModel, devaluation: float, *, exchange_effect: float
) -> ASADShift:
    """A devaluation of size ``devaluation`` (a fall in the value of the currency).

    Aggregate demand shifts right by ``exchange_effect * devaluation`` (autonomous demand).
    """
    if devaluation < 0:
        raise ValidationError("a devaluation cannot be negative")
    if exchange_effect < 0:
        raise ValidationError("the exchange effect cannot be negative")
    return analyze_demand_shock(
        model, autonomous=model.demand.autonomous + exchange_effect * devaluation
    )
