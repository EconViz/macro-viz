"""The curves of each panel, computed from the solved states; no drawing, no text.

A curve belongs to a *family* (labour demand, SRAS, LM ...) and has a *key*, the parameters
that make it a different curve (price level and capital for labour demand ...). The curve of the
first step is the main one; a curve another step brings is drawn thin. Label text is described
by ``Subscripted`` symbols (a variable and the step index of its subscript) and resolved
against the locale table by the visual builder.

``Mode.DERIVED`` draws each curve from the model equations. ``Mode.SCHEMATIC`` (the textbook
picture) draws straight lines through the solved points instead, so the lines pass through
the dots whatever the curvature of the equations; the solved values are identical in both."""

from __future__ import annotations

from macro_viz.adas.linked.curves._geometry import clip, price_symbol
from macro_viz.adas.linked.curves._types import (
    DEFAULT_SAMPLES,
    HORIZONTAL,
    KEY_DIGITS,
    VERTICAL,
    CurveOptions,
    CurveSpec,
    Mode,
    Point,
    Subscripted,
)
from macro_viz.adas.linked.curves.builder import curve_specs, sample_rate
from macro_viz.adas.linked.curves.ranges import Ranges, axis_lengths

__all__ = [
    "HORIZONTAL",
    "VERTICAL",
    "Point",
    "DEFAULT_SAMPLES",
    "KEY_DIGITS",
    "Mode",
    "Subscripted",
    "CurveSpec",
    "CurveOptions",
    "price_symbol",
    "clip",
    "Ranges",
    "axis_lengths",
    "curve_specs",
    "sample_rate",
]
