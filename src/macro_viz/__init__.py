"""Textbook macroeconomic analysis and diagrams for EconViz."""

from macro_viz.config import Config
from macro_viz.errors import MacroVizError, ValidationError

__version__ = "0.2.0.dev0"

__all__ = [
    "Config",
    "MacroVizError",
    "ValidationError",
    "__version__",
]
