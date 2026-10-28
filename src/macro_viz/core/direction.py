"""The sign of a comparative-statics change, shared by every model."""

from __future__ import annotations

from enum import Enum


class Direction(str, Enum):
    """The sign of a change."""

    UP = "up"
    DOWN = "down"
    NONE = "none"

    @classmethod
    def of(cls, change: float, tolerance: float = 0.0) -> Direction:
        """``UP`` above ``tolerance``, ``DOWN`` below ``-tolerance``, otherwise ``NONE``."""
        return cls.UP if change > tolerance else cls.DOWN if change < -tolerance else cls.NONE
