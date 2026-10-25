"""Which group a macro-viz label belongs to, for the label nudges in ``econ-viz.toml``.

``[macro.label.<group>]`` moves every label of a group by default. The groups follow what a
label names:

``point``
    Dots: equilibrium and path points (``A``, ``A'``, ``B``).
``curve``
    Curves named beside their end (``IS``, ``LM``, ``AD``, ``AS``, ``Md``, ``ZZ``).
``mark``
    Values and marks on the figure (``Y*``, ``i``, price levels).
``region``
    Names inside filled regions (gaps, brackets drawn as areas).
``annotation``
    Everything else that is text: brackets, shift sizes, notes.

Axis titles and axis marks belong to no group: they cannot be nudged.
"""

from __future__ import annotations

from mosaickit import (
    AxisMarkLayer,
    AxisNoteLayer,
    BraceLayer,
    Layer,
    PointLabelLayer,
    RegionLabelLayer,
    SpanBraceLayer,
    TextLayer,
)

LABEL_GROUPS = ("point", "curve", "mark", "region", "annotation")
"""The label groups, in the order of ``[macro.label.<group>]``."""

LABEL_SIDES = ("top", "bottom", "left", "right")
"""The directions of a nudge, as in mosaickit ``Nudge``."""


def _under(role: str, prefix: str) -> bool:
    return role == prefix or role.startswith(f"{prefix}.")


def label_group(layer: Layer) -> str | None:
    """The group of ``layer``'s label, or ``None`` for one that takes no default nudge."""
    if isinstance(layer, (AxisMarkLayer, AxisNoteLayer)):
        return None
    if isinstance(layer, RegionLabelLayer):
        return "region"
    if isinstance(layer, (PointLabelLayer, TextLayer)):
        if layer.id.startswith("axes."):
            return None
        if _under(layer.role, "macro.point"):
            return "point"
        if _under(layer.role, "macro.curve"):
            return "curve"
        if _under(layer.role, "macro.mark"):
            return "mark"
        return "annotation"
    if isinstance(layer, (BraceLayer, SpanBraceLayer)):
        return "annotation"
    return None
