"""Renderer-neutral building blocks shared by every macro-viz figure.

A figure is a list of public MosaicKit layers on a ``Canvas``. This module holds the parts
every figure needs: the canvas that applies the label-group nudges of the configuration,
axes with arrowheads and their titles. It names no colour, font,
or size: those come from the theme roles of ``macro_viz.themes`` and the configuration.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import replace
from typing import Any

from mosaickit import (
    ArrowPlacement,
    ArrowStyle,
    Canvas,
    CanvasSpec,
    Layer,
    PathLayer,
    Stroke,
    TextLayer,
)
from mosaickit.layout.labels import LabelOptions, PlacementWarning
from mosaickit.styles.nudge import Nudge

from macro_viz.config import active_config
from macro_viz.label_groups import label_group
from macro_viz.visuals._labels import (
    LABEL_OPTIONS,
    NAME_SUFFIX,
    Frame,
    LabelSpec,
    axes_frame,
    figure_frame,
    place_canvas_labels,
    report,
)

TITLE_GAP = 6.0
"""Gap between an arrow tip and its axis title, in points."""


class MacroCanvas(Canvas):
    """A MosaicKit canvas that nudges labels by group and places its movable labels once.

    Curve names (a text whose id is its curve's id plus ``.label``) are registered when they
    are added; points and ticks are registered with ``add_label``. Every movable label is
    placed together, against the whole scene, when the figure is first read after a change.
    """

    def __init__(
        self,
        *args: Any,
        label_nudges: Mapping[str, Nudge] | None = None,
        axes_size: tuple[float, float] | None = None,
        label_options: LabelOptions = LABEL_OPTIONS,
        **kwargs: Any,
    ):
        self._label_nudges = dict(label_nudges or {})
        self._spec: CanvasSpec | None = args[0] if args else kwargs.get("spec")
        self._axes_size = axes_size
        self._label_options = label_options
        self._specs: dict[str, LabelSpec] = {}
        self._leaders: tuple[str, ...] = ()
        self._names_stale = False
        self.label_warnings: tuple[PlacementWarning, ...] = ()
        super().__init__(*args, **kwargs)

    @property
    def _scene(self) -> Any:
        """The scene with every movable label placed; placing waits until something reads it."""
        if self._names_stale:
            self._place_labels()
        return self._placed_scene

    @_scene.setter
    def _scene(self, scene: Any) -> None:
        self._placed_scene = scene

    def _nudged(self, layer: Layer) -> Layer:
        group = label_group(layer)
        nudge = self._label_nudges.get(group) if group else None
        if nudge is None or not hasattr(layer, "nudge"):
            return layer
        current: Nudge | None = getattr(layer, "nudge", None)
        if current is not None:
            nudge = Nudge(current.dx + nudge.dx, current.dy + nudge.dy)
        return replace(layer, nudge=nudge)  # type: ignore[call-arg]

    def _register(self, layer: Layer) -> None:
        if _is_curve_name(layer) and layer.id not in self._specs:
            self._specs[layer.id] = LabelSpec(layer.id[: -len(NAME_SUFFIX)])

    def add(self, layer: Layer) -> MacroCanvas:
        self._placed_scene = self._placed_scene.add(self._nudged(layer))
        self._register(layer)
        self._names_stale = True
        return self

    def extend(self, layers: Iterable[Layer]) -> MacroCanvas:
        found = list(layers)
        self._placed_scene = self._placed_scene.extend([self._nudged(layer) for layer in found])
        for layer in found:
            self._register(layer)
        self._names_stale = True
        return self

    def add_label(self, layer: TextLayer, spec: LabelSpec) -> MacroCanvas:
        """Add a text the placer moves: a name, a point's label or a tick label."""
        self._specs[layer.id] = spec
        return self.add(layer)

    def _frame(self) -> Frame:
        spec = self._spec
        assert spec is not None
        if self._axes_size is not None:
            return axes_frame(spec.x_range, spec.y_range, self._axes_size)
        return figure_frame(spec.x_range, spec.y_range, spec.width, spec.height)

    def _place_labels(self) -> None:
        """Place every movable label together; leaders of an earlier pass are dropped first."""
        self._names_stale = False
        if self._spec is None or not self._specs:
            return
        scene = self._placed_scene
        layers = [layer for layer in scene.layers if layer.id not in self._leaders]
        placed, found = place_canvas_labels(
            layers,
            self._specs,
            self._frame(),
            theme=self.theme,
            config=self.config,
            options=self._label_options,
        )
        leaders = tuple(i for i in placed if i not in self._specs)
        replaced = [placed.get(layer.id, layer) for layer in layers]
        self._leaders = leaders
        self._placed_scene = replace(scene, layers=(*replaced, *(placed[i] for i in leaders)))
        self.label_warnings = found
        report(found, self._spec.title or "figure")


def _is_curve_name(layer: Layer) -> bool:
    return (
        isinstance(layer, TextLayer)
        and layer.id.endswith(NAME_SUFFIX)
        and (layer.role == "macro.curve" or layer.role.startswith("macro.curve."))
    )


def new_canvas(
    spec: CanvasSpec,
    *,
    axes_size: tuple[float, float] | None = None,
    label_options: LabelOptions = LABEL_OPTIONS,
) -> MacroCanvas:
    """Create a canvas with the active macro-viz MosaicKit configuration.

    ``axes_size`` is the real size in points of its axes when it sits in a grid.
    """
    settings = active_config().settings
    return MacroCanvas(
        spec,
        config=settings.mosaickit_config(),
        label_nudges=settings.label_nudges,
        axes_size=axes_size,
        label_options=label_options,
    )


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
