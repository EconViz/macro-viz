"""Textbook macroeconomic analysis and diagrams for EconViz."""

from macro_viz.core.config import Config
from macro_viz.core.errors import LabelPlacementWarning, MacroVizError, ValidationError

__version__ = "1.0.0b1"

__all__ = [
    "Config",
    "LabelPlacementWarning",
    "MacroVizError",
    "ValidationError",
    "__version__",
]
