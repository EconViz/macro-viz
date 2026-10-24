"""Public exceptions raised by macro-viz."""


class MacroVizError(Exception):
    """Base class for macro-viz errors."""


class ValidationError(MacroVizError, ValueError):
    """Input data violates an economic or time-series constraint."""
