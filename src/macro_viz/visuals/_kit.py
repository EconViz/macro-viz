"""Renderer-neutral building blocks shared by every macro-viz figure.

A figure is a list of public MosaicKit layers on a ``Canvas``. This module holds the parts
every figure needs: the canvas that applies the label-group nudges of the configuration,
axes with arrowheads, tick selection, and direct curve labels. It names no colour, font,
or size: those come from the theme roles of ``macro_viz.themes`` and the configuration.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import replace
from typing import Any

from mosaickit import (
    ArrowPlacement,
    ArrowStyle,
    AxisMarkLayer,
    Canvas,
    CanvasSpec,
    Layer,
    PathLayer,
    PointLabelLayer,
    Stroke,
    TextLayer,
)
from mosaickit.styles.nudge import Nudge

from macro_viz.config import active_config
from macro_viz.errors import ValidationError
from macro_viz.label_groups import label_group

TITLE_GAP = 6.0
"""Gap between an arrow tip and its axis title, in points."""

LINE_SHARE = 1.4
"""Height of a line of text as a multiple of its font size, for lifting a title above it."""

DEFAULT_MARKS = 5
"""How many value marks a continuous axis shows when the caller does not say."""


class MacroCanvas(Canvas):
    """A MosaicKit canvas that moves each label by its group's default nudge."""

    def __init__(self, *args: Any, label_nudges: Mapping[str, Nudge] | None = None, **kwargs: Any):
        self._label_nudges = dict(label_nudges or {})
        super().__init__(*args, **kwargs)

    def _nudged(self, layer: Layer) -> Layer:
        group = label_group(layer)
        nudge = self._label_nudges.get(group) if group else None
        if nudge is None or not hasattr(layer, "nudge"):
            return layer
        current: Nudge | None = getattr(layer, "nudge", None)
        if current is not None:
            nudge = Nudge(current.dx + nudge.dx, current.dy + nudge.dy)
        return replace(layer, nudge=nudge)  # type: ignore[call-arg]

    def add(self, layer: Layer) -> MacroCanvas:
        super().add(self._nudged(layer))
        return self

    def extend(self, layers: Iterable[Layer]) -> MacroCanvas:
        super().extend([self._nudged(layer) for layer in layers])
        return self


def new_canvas(spec: CanvasSpec) -> MacroCanvas:
    """Create a canvas with the active macro-viz MosaicKit configuration."""
    settings = active_config().settings
    return MacroCanvas(spec, config=settings.mosaickit_config(), label_nudges=settings.label_nudges)


def canvas_spec(
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    *,
    width: float,
    height: float,
    title: str | None,
) -> CanvasSpec:
    """A canvas whose axis titles are drawn by ``axes_layers``, not by the renderer."""
    return CanvasSpec(
        x_range=x_range,
        y_range=y_range,
        width=width,
        height=height,
        x_label="",
        y_label="",
        title=title,
    )


def nice_step(span: float, count: int) -> float:
    """A 1, 2, or 5 times a power of ten that splits ``span`` into about ``count`` steps."""
    if span <= 0 or count < 1:
        raise ValidationError("a tick step needs a positive span and count")
    raw = span / count
    power = 10 ** math.floor(math.log10(raw))
    for factor in (1, 2, 5):
        if raw <= factor * power:
            return float(factor * power)
    return float(10 * power)


def nice_bounds(low: float, high: float, count: int = DEFAULT_MARKS) -> tuple[float, float, float]:
    """Round ``low`` and ``high`` outward to multiples of a nice step: (low, high, step)."""
    if high < low:
        raise ValidationError("a range needs low <= high")
    if high == low:
        pad = abs(high) * 0.1 or 1.0
        low, high = low - pad, high + pad
    step = nice_step(high - low, count)
    return (math.floor(low / step) * step, math.ceil(high / step) * step, step)


def tick_values(low: float, high: float, step: float) -> tuple[float, ...]:
    """The multiples of ``step`` inside ``[low, high]``, free of floating-point noise."""
    first = math.ceil(low / step - 1e-9)
    last = math.floor(high / step + 1e-9)
    digits = max(0, -math.floor(math.log10(step)) + 1)
    return tuple(round(k * step, digits) for k in range(first, last + 1))


def is_symbol(label: str) -> bool:
    """Single letters and ``$...$`` titles are set as math; words stay upright."""
    wrapped = len(label) > 1 and label.startswith("$") and label.endswith("$")
    return wrapped or (len(label) == 1 and label.isalpha())


def axes_layers(
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    *,
    x_label: str | None,
    y_label: str | None,
    origin_label: str | None = None,
) -> list[Layer]:
    """Axes with arrowheads from the lower-left corner, and their titles past the tips.

    A symbol title (``Y``, ``$i$``) sits right of the x arrow; a word ends at the tip, under
    the arrow. ``origin_label`` (usually ``"0"``) is drawn at the corner when given.
    """
    x0, x1 = x_range
    y0, y1 = y_range
    arrow = Stroke(arrow=ArrowStyle.TRIANGLE)
    layers: list[Layer] = [
        PathLayer(
            ((x0, y0), (x1, y0)),
            id="axes.x",
            role="axes",
            stroke=arrow,
            arrow_placement=ArrowPlacement.END,
            clip=False,
        ),
        PathLayer(
            ((x0, y0), (x0, y1)),
            id="axes.y",
            role="axes",
            stroke=arrow,
            arrow_placement=ArrowPlacement.END,
            clip=False,
        ),
    ]
    if y_label:
        layers.append(
            TextLayer(
                (x0, y1),
                y_label,
                id="axes.y.label",
                role="axes",
                anchor="bottom",
                offset=(0, TITLE_GAP),
                math=is_symbol(y_label),
            )
        )
    if x_label:
        symbol = is_symbol(x_label)
        layers.append(
            TextLayer(
                (x1, y0),
                x_label,
                id="axes.x.label",
                role="axes",
                anchor="left" if symbol else "top-right",
                offset=(TITLE_GAP, 0) if symbol else (0, -TITLE_GAP),
                math=symbol,
            )
        )
    if origin_label:
        layers.append(
            TextLayer(
                (x0, y0),
                origin_label,
                id="axes.origin.label",
                role="axes",
                anchor="right",
                offset=(-7, -7),
            )
        )
    return layers


def value_marks(
    axis: str,
    values: Sequence[float],
    *,
    value_format: str,
    id_prefix: str,
) -> list[AxisMarkLayer]:
    """Axis marks for ``values`` on ``axis``, labelled with ``value_format``."""
    return [
        AxisMarkLayer(
            axis,
            value,
            value_format.format(value),
            id=f"{id_prefix}.{index}",
            role="axes",
        )
        for index, value in enumerate(values)
    ]


def direct_label(
    point: tuple[float, float], text: str, *, layer_id: str, role: str
) -> PointLabelLayer:
    """A curve or series name placed right beside ``point``, covering nothing else."""
    return PointLabelLayer(point, text, id=layer_id, role=role)


def title_layer(
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    title: str,
    *,
    above_label: bool = False,
) -> TextLayer:
    """The figure title, centred over the axes.

    With ``above_label`` it is lifted by one text line, so that it clears a word title
    (a unit) written above the vertical axis.
    """
    options = active_config().settings.options
    lift = options.label_size * options.text_scale * LINE_SHARE if above_label else 0.0
    return TextLayer(
        ((x_range[0] + x_range[1]) / 2, y_range[1]),
        title,
        id="macro.title",
        role="title",
        anchor="bottom",
        offset=(0, 2 * TITLE_GAP + lift),
    )
