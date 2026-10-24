"""Business-cycle trend and turning-point analysis."""

from macro_viz.cycles.analysis import analyze_business_cycle, linear_trend
from macro_viz.cycles.models import (
    BusinessCycleResult,
    RecessionPeriod,
    TurningPoint,
    TurningPointKind,
)

__all__ = [
    "BusinessCycleResult",
    "RecessionPeriod",
    "TurningPoint",
    "TurningPointKind",
    "analyze_business_cycle",
    "linear_trend",
]
