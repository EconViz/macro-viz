"""Macro-viz semantic roles compiled from MosaicKit shared theme tokens.

The colours come from a shared theme (``manual``, ``default``, ...); the sizes below are
documented defaults that the ``[macro.*]`` table of ``econ-viz.toml`` overrides (see
``macro_viz.config``). Nothing here names a colour or a font file.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from mosaickit import ArrowStyle, DashStyle, Fill, Marker, Stroke, StyleBundle, TextStyle, Theme
from mosaickit.themes import ThemeTokens, get_tokens, list_shared_themes

WHITE = str(get_tokens("manual").color("background"))
"""The background of themes without one: figures are never drawn on a dark ground."""


@dataclass(frozen=True, slots=True)
class ThemeOptions:
    """Concrete visual options produced by the macro-viz configuration schema.

    Widths and diameters are in points; ``point_size`` is the marker area, the square of its
    diameter. Text sizes are in points and are multiplied by ``text_scale``.
    """

    name: str
    background: str | None
    axis: str
    label: str
    primary: str
    secondary: str
    tertiary: str
    curve_width: float = 3.5
    shifted_width: float = 1.0
    line45_width: float = 0.8
    arrow_width: float = 1.0
    guide_width: float = 1.0
    link_width: float = 0.7
    diagonal_width: float = 0.6
    point_size: float = 42.25
    font: str = "sans"
    label_size: float = 11.0
    annotation_size: float = 10.0
    title_size: float = 12.0
    text_scale: float = 1.0


def options_from_tokens(tokens: ThemeTokens, *, font: str = "sans") -> ThemeOptions:
    """Map shared tokens onto the visual roles used by macro diagrams."""

    def color(role: str) -> str:
        value = tokens.color(role)
        if value is None:
            raise ValueError(f"theme role {role!r} requires a color")
        return value

    base = ThemeOptions(
        name=tokens.name,
        background=tokens.color("background") or WHITE,
        axis=color("ink"),
        label=color("ink"),
        primary=color("primary"),
        secondary=color("secondary"),
        tertiary=color("tertiary"),
        font=font,
    )
    return replace(
        base,
        curve_width=base.curve_width * tokens.line_scale,
        shifted_width=base.shifted_width * tokens.line_scale,
        arrow_width=base.arrow_width * tokens.line_scale,
        guide_width=base.guide_width * tokens.line_scale,
        link_width=base.link_width * tokens.line_scale,
        diagonal_width=base.diagonal_width * tokens.line_scale,
        point_size=base.point_size * tokens.marker_scale**2,
        text_scale=tokens.label_scale,
    )


def _text(
    options: ThemeOptions, color: str, size: float, *, weight: str | None = None
) -> TextStyle:
    return TextStyle(color=color, size=size * options.text_scale, font=options.font, weight=weight)


def build_theme(options: ThemeOptions) -> Theme:
    """Build a MosaicKit theme with stable ``macro.*`` semantic roles."""
    o = options
    label = _text(o, o.label, o.label_size)
    small = _text(o, o.label, o.annotation_size)
    curves = {"primary": o.primary, "secondary": o.secondary, "tertiary": o.tertiary}
    roles: dict[str, StyleBundle] = {
        "canvas": StyleBundle(
            fill=Fill(
                color=o.background or o.axis,
                opacity=1.0 if o.background is not None else 0.0,
            )
        ),
        "axes": StyleBundle(stroke=Stroke(color=o.axis, width=1.0), text=label),
        "title": StyleBundle(text=_text(o, o.label, o.title_size)),
        # Theory curves: heavy lines named at their ends; the old position is thin and dashed.
        "macro.curve": StyleBundle(stroke=Stroke(color=o.axis, width=o.curve_width)),
        "macro.line45": StyleBundle(
            stroke=Stroke(color=o.axis, width=o.line45_width, arrow=ArrowStyle.TRIANGLE),
            text=small,
        ),
        "macro.mark": StyleBundle(text=small),
        "macro.annotation": StyleBundle(text=small),
        "macro.annotation.strong": StyleBundle(
            text=_text(o, o.label, o.annotation_size + 2, weight="bold")
        ),
        "macro.guide": StyleBundle(
            stroke=Stroke(color=o.axis, width=o.guide_width, dash=DashStyle.DASHED), text=small
        ),
        "macro.movement": StyleBundle(
            stroke=Stroke(color=o.axis, width=o.arrow_width, dash=DashStyle.DASHED), text=small
        ),
        "macro.point": StyleBundle(
            marker=Marker(color=o.axis, size=o.point_size, edge_color=o.axis, edge_width=0),
            text=label,
        ),
        "macro.point.shifted": StyleBundle(
            marker=Marker(color=o.tertiary, size=o.point_size, edge_color=o.tertiary, edge_width=0),
            text=_text(o, o.tertiary, o.label_size),
        ),
    }
    roles.update(
        {
            # Linked panels: bold main curves, thin grey shifted ones, thin dashed links.
            "macro.curve.panel": StyleBundle(
                stroke=Stroke(color=o.axis, width=o.curve_width), text=label
            ),
            "macro.curve.panel.shifted": StyleBundle(
                stroke=Stroke(color=o.tertiary, width=o.shifted_width), text=label
            ),
            "macro.link": StyleBundle(
                stroke=Stroke(color=o.axis, width=o.link_width, dash=DashStyle.DASHED)
            ),
            "macro.diagonal": StyleBundle(stroke=Stroke(color=o.axis, width=o.diagonal_width)),
            "macro.shift": StyleBundle(stroke=Stroke(color=o.axis, width=o.arrow_width)),
        }
    )
    for name, color in curves.items():
        roles[f"macro.curve.{name}"] = StyleBundle(
            stroke=Stroke(color=color, width=o.curve_width),
            text=_text(o, color, o.label_size),
        )
        roles[f"macro.curve.{name}.shifted"] = StyleBundle(
            stroke=Stroke(color=color, width=o.shifted_width, dash=DashStyle.DASHED)
        )
    return Theme(o.name, roles, defaults=StyleBundle(text=TextStyle(font=o.font)))


def get_theme(name: str) -> Theme:
    """Return a built-in macro-viz theme by shared theme name."""
    return build_theme(options_from_tokens(get_tokens(name)))


def list_themes() -> tuple[str, ...]:
    """Names of the shared themes available to macro-viz."""
    return list_shared_themes()


MANUAL_THEME = get_theme("manual")

__all__ = [
    "MANUAL_THEME",
    "ThemeOptions",
    "build_theme",
    "get_theme",
    "list_themes",
    "options_from_tokens",
]
