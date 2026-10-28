"""Linked panels that derive IS, LM, AD, and AS from their component markets."""

from macro_viz.adas.visuals.derivation.ad import ad_derivation_canvas
from macro_viz.adas.visuals.derivation.as_derivation import as_derivation_canvas
from macro_viz.islm.visuals.derivation.is_derivation import is_derivation_canvas
from macro_viz.islm.visuals.derivation.lm import lm_derivation_canvas

__all__ = [
    "ad_derivation_canvas",
    "as_derivation_canvas",
    "is_derivation_canvas",
    "lm_derivation_canvas",
]
