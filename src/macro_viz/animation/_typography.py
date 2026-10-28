"""Label text prepared for GlyphKit typesetting."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from macro_viz.core.config import active_config
from macro_viz.core.errors import ValidationError


def _horizontal(anchor: str) -> str:
    return (
        "left"
        if anchor.endswith("left") or anchor == "left"
        else ("right" if anchor.endswith("right") or anchor == "right" else "center")
    )


def _vertical(anchor: str) -> str:
    return (
        "top" if anchor.startswith("top") else "bottom" if anchor.startswith("bottom") else "center"
    )


def _plain(label: str, math: bool) -> str:
    """Axis-mark text as a ``$...$`` formula when it is math."""
    return f"${label}$" if math else label


class _Typography:
    """GlyphKit text assets in the configured fonts, one typography per font size."""

    def __init__(self) -> None:
        from glyphkit import FontLibrary, FontSource

        settings = active_config().settings
        fonts = settings.fonts
        faces = tuple(getattr(fonts, "serif", ()) or ()) if fonts is not None else ()
        if not faces:
            raise ValidationError(
                "animated SVG needs font files: set [fonts] in econ-viz.toml "
                "(for example serif = [...]) and [font] math"
            )
        self._text = self._library(FontLibrary, FontSource, faces)
        math_font = settings.math_font
        self._math = (
            self._library(FontLibrary, FontSource, (Path(math_font.path),))
            if math_font is not None
            else None
        )
        self._cache: dict[tuple[str, float], Any] = {}

    @staticmethod
    def _library(library: Any, source: Any, paths: Sequence[Any]) -> tuple[Any, tuple[str, ...]]:
        fonts = library.from_sources(tuple(source.path(Path(path)) for path in paths))
        return fonts, tuple(dict.fromkeys(face.family for face in fonts.faces))

    def _typography(self, kind: str, size: float) -> Any:
        from kinetickit.integrations.glyphkit import GlyphKitTypography

        key = (kind, size)
        if key not in self._cache:
            library, families = self._math if kind == "math" and self._math else self._text
            self._cache[key] = GlyphKitTypography(library, families=families, size=size)
        return self._cache[key]

    def asset(self, label: str, size: float) -> Any:
        is_math = len(label) > 2 and label.startswith("$") and label.endswith("$")
        if is_math and self._math is not None:
            return self._typography("math", size).math(label[1:-1])
        return self._typography("text", size).asset(label.strip("$") if is_math else label)
