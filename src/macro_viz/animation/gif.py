"""Frames of a builder and the GIF exporter."""

from __future__ import annotations

import tempfile
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

from macro_viz.animation._preset import DEFAULT_DPI, DEFAULT_FPS, Builder
from macro_viz.core.errors import ValidationError


def linear_values(start: float, stop: float, frames: int) -> tuple[float, ...]:
    """``frames`` evenly spaced values from ``start`` to ``stop`` inclusive."""
    if isinstance(frames, bool) or not isinstance(frames, int) or frames < 2:
        raise ValidationError("an animation needs at least two frames")
    step = (stop - start) / (frames - 1)
    return tuple(start + k * step for k in range(frames))


def frames(builder: Builder, values: Sequence[float]) -> list[Any]:
    """The canvas of ``builder`` at each of ``values``."""
    if not values:
        raise ValidationError("an animation needs at least one value")
    return [builder(float(value)) for value in values]


def _require_kinetickit() -> None:
    try:
        import kinetickit  # noqa: F401
    except ImportError as error:
        raise ImportError(
            "KineticKit is required to animate figures.\n"
            "Install it with:  pip install macro-viz[animation]"
        ) from error


def _png_frames(builder: Builder, values: Sequence[float], dpi: int, stem: str) -> Iterator[bytes]:
    """PNG bytes of every frame, padded with white to one common size.

    Labels that change width (a mark ``p'`` against ``p''``) make the tight bounding box differ
    from frame to frame; a GIF needs one size.
    """
    import io

    from PIL import Image

    with tempfile.TemporaryDirectory(prefix="macro-viz-animation-") as directory:
        images: list[Image.Image] = []
        for index, canvas in enumerate(frames(builder, values)):
            options: dict[str, Any] = {"transparent": False}
            if hasattr(canvas, "spec"):
                canvas.spec = canvas.spec.replace(dpi=dpi)
            else:  # a grid renders at the highest resolution of its cells
                for placement in canvas.placements:
                    placement.canvas.spec = placement.canvas.spec.replace(dpi=dpi)
            # Named after the animation, so per-figure label overrides reach every frame.
            target = Path(directory) / f"{index:06d}" / f"{stem}.png"
            target.parent.mkdir(parents=True, exist_ok=True)
            canvas.save(target, **options)
            with Image.open(target) as opened:
                images.append(opened.convert("RGB"))
        width = max(image.width for image in images)
        height = max(image.height for image in images)
        for image in images:
            padded = Image.new("RGB", (width, height), "white")
            padded.paste(image, (0, 0))
            buffer = io.BytesIO()
            padded.save(buffer, format="PNG")
            yield buffer.getvalue()


def save_gif(
    builder: Builder,
    values: Sequence[float],
    path: str | Path,
    *,
    fps: int = DEFAULT_FPS,
    dpi: int = DEFAULT_DPI,
    loop: int = 0,
) -> Path:
    """Render ``builder`` at each value through MosaicKit and write a GIF with KineticKit."""
    _require_kinetickit()
    try:
        from kinetickit.exporters import export_png_frames
    except ImportError as error:
        raise ImportError(
            "KineticKit's raster capability is required for GIF export.\n"
            "Install it with:  pip install macro-viz[animation]"
        ) from error
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    export_png_frames(
        _png_frames(builder, values, dpi, target.stem), target, fps=fps, loop=loop, disposal=2
    )
    return target
