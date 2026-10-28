"""MosaicKit's ``Diagram`` wired to macro-viz: locale labels, theme roles, configured nudges.

Figures that declare their panels with :func:`panel` get the arrowed axes titled from the
locale ids, the ``macro.*`` roles for points, guides and arrows, the ``[macro.label.*]``
nudges of the configuration, and the curve-name placement tuned for macro-viz, without each
figure repeating that wiring.
"""

from __future__ import annotations

from typing import Any

from mosaickit import Layer
from mosaickit.diagram import Diagram
from mosaickit.layout import View
from mosaickit.styles.nudge import Nudge

from macro_viz.core.config import active_config
from macro_viz.core.i18n import Labels
from macro_viz.core.label_groups import label_group

PRIMARY = "macro.curve.primary"
"""Role of a curve that carries the argument of the figure."""
SECONDARY = "macro.curve.secondary"
"""Role of a secondary curve: the baseline position of a shifting curve."""
SHIFTED = "macro.curve.secondary.shifted"
"""Role of a secondary curve after it has shifted."""
POINT = "macro.point"
GUIDE = "macro.guide"
MOVEMENT = "macro.movement"
LINK = "macro.link"
"""Roles of points, dotted guides, shift arrows and the links between linked panels."""

DIAGONAL_NAME_SHARE = 0.75
"""Share of the name gap a diagonal curve name keeps from its curve end."""
ORIGIN_LABEL_ID = "axis.origin"
"""Locale id of the label at the corner of the axes."""


def _nudge(layer: Layer) -> Nudge | None:
    """The configured default nudge of a label's group; axis titles take none."""
    group = label_group(layer)
    return active_config().settings.label_nudges.get(group) if group else None


class MacroDiagram(Diagram):
    """A ``Diagram`` whose points, guides and arrows take the ``macro.*`` roles by default."""

    def point(self, *args: Any, **kwargs: Any) -> MacroDiagram:
        kwargs.setdefault("role", POINT)
        super().point(*args, **kwargs)
        return self

    def guide(self, *args: Any, **kwargs: Any) -> MacroDiagram:
        kwargs.setdefault("role", GUIDE)
        super().guide(*args, **kwargs)
        return self

    def drop(self, *args: Any, **kwargs: Any) -> MacroDiagram:
        kwargs.setdefault("role", GUIDE)
        super().drop(*args, **kwargs)
        return self

    def arrow(self, *args: Any, **kwargs: Any) -> MacroDiagram:
        kwargs.setdefault("role", MOVEMENT)
        super().arrow(*args, **kwargs)
        return self


def panel(
    text: Labels,
    x_label: str,
    y_label: str,
    *,
    view: View | None = None,
    x_max: float | None = None,
    y_max: float | None = None,
    title: str | None = None,
    width: float,
    height: float,
    rising_names_upper_right: bool = False,
) -> MacroDiagram:
    """One panel with arrowed axes titled by the locale ids ``x_label`` and ``y_label``."""
    settings = active_config().settings
    return MacroDiagram(
        x_max,
        y_max,
        view=view,
        x_label=text(x_label),
        y_label=text(y_label),
        origin_label=text(ORIGIN_LABEL_ID),
        title=title,
        width=width,
        height=height,
        config=settings.mosaickit_config(),
        nudge=_nudge,
        rising_names_upper_right=rising_names_upper_right,
        font_size=settings.options.label_size * settings.options.text_scale,
        name_diagonal=DIAGONAL_NAME_SHARE,
    )
