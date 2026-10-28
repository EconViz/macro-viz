"""Public exceptions raised by macro-viz."""


class MacroVizError(Exception):
    """Base class for macro-viz errors."""


class ValidationError(MacroVizError, ValueError):
    """Input data violates an economic or time-series constraint."""


class LabelPlacementWarning(UserWarning):
    """A label could not be placed free of collisions, or its text could not be measured."""
