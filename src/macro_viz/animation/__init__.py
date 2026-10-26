"""Animate any figure builder over a parameter with KineticKit (optional dependency).

A *builder* is a function from one number (a shift, a saving rate, a round) to a MosaicKit
canvas: the very function that draws the static figure, with every range fixed by the caller so
the axes stay put. The frames are that builder's canvases at each value, so the animated and
the static figure share one geometry source and there is no second drawing code.

``save_gif`` renders every frame through MosaicKit and streams the pixels through KineticKit's
GIF exporter (``pip install macro-viz[animation]``). ``save_svg`` depicts the frames' layers as
KineticKit nodes keyed by their stable ids and lets KineticKit morph between frames into a native
animated SVG; it typesets labels with GlyphKit from the font files of the active configuration
(``[font]`` and ``[fonts]`` of ``econ-viz.toml``). Static figures never import KineticKit.
"""

from __future__ import annotations

from macro_viz.animation._preset import DEFAULT_DPI, DEFAULT_FPS, DEFAULT_STEP_SECONDS, Builder
from macro_viz.animation.gif import frames, linear_values, save_gif
from macro_viz.animation.svg import save_svg

__all__ = [
    "DEFAULT_DPI",
    "DEFAULT_FPS",
    "DEFAULT_STEP_SECONDS",
    "Builder",
    "frames",
    "linear_values",
    "save_gif",
    "save_svg",
]
