"""Linked panels that derive IS, LM, AD, and AS from their component markets."""

from macro_viz.visuals.transmission.ad_derivation import ad_derivation_canvas
from macro_viz.visuals.transmission.as_derivation import as_derivation_canvas
from macro_viz.visuals.transmission.is_derivation import is_derivation_canvas
from macro_viz.visuals.transmission.lm_derivation import lm_derivation_canvas

__all__ = [
    "ad_derivation_canvas",
    "as_derivation_canvas",
    "is_derivation_canvas",
    "lm_derivation_canvas",
]
