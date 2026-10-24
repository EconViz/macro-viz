"""Textbook macroeconomic analysis and diagrams for EconViz."""

from macro_viz.config import Config
from macro_viz.errors import MacroVizError, ValidationError
from macro_viz.series import IndexBase, TimeSeries

__version__ = "0.2.0.dev0"

__all__ = [
    "Config",
    "IndexBase",
    "MacroVizError",
    "TimeSeries",
    "ValidationError",
    "__version__",
]
