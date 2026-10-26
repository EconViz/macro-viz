"""The animated SVG exporter."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from mosaickit import (
    Canvas,
    Layer,
)

from macro_viz.errors import ValidationError

if TYPE_CHECKING:  # pragma: no cover
    from kinetickit.scene.node import Node

from macro_viz.animation._depicter import _Depicter
from macro_viz.animation._geometry import _geometry
from macro_viz.animation._preset import DEFAULT_STEP_SECONDS, MARGIN_POINTS, Builder
from macro_viz.animation._typography import _Typography
from macro_viz.animation.gif import _require_kinetickit, frames


def save_svg(
    builder: Builder,
    values: Sequence[float],
    path: str | Path,
    *,
    step_seconds: float = DEFAULT_STEP_SECONDS,
    margin: tuple[float, float, float, float] = MARGIN_POINTS,
) -> Path:
    """Morph between ``builder``'s frames into a native animated SVG with KineticKit."""
    _require_kinetickit()
    if len(values) < 2:
        raise ValidationError("an animated SVG needs at least two frames")
    from kinetickit.adapters import transition
    from kinetickit.animation import Animation
    from kinetickit.geometry.two_d import Bounds2D, Vec2

    canvases = [canvas for canvas in frames(builder, values) if isinstance(canvas, Canvas)]
    if len(canvases) != len(values):
        raise ValidationError("an animated SVG needs single canvases; use save_gif for panels")
    geometry = _geometry(canvases[0], margin)
    typography = _Typography()
    layer_sets = [list(canvas.snapshot().layers) for canvas in canvases]
    per_frame = [_Depicter(canvas, geometry, typography) for canvas in canvases]
    depicters = {
        id(layer): depicter
        for depicter, layers in zip(per_frame, layer_sets, strict=True)
        for layer in layers
    }

    def depict(layer: Layer) -> list[Node]:
        return depicters[id(layer)](layer)

    steps = [
        transition(before, after, depict, duration=step_seconds)
        for before, after in zip(layer_sets, layer_sets[1:], strict=False)
    ]
    motion = steps[0].motion
    for step in steps[1:]:
        motion = motion.then(step.motion)
    scene = steps[0].scene
    view = Bounds2D(Vec2(0.0, 0.0), Vec2(geometry.width, geometry.height))
    scene = scene.bind({scene.camera.ref("view"): view})
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    Animation(scene, motion).save(
        target, renderer="vector", width=geometry.width, height=geometry.height
    )
    return target
