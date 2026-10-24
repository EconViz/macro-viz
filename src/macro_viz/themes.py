"""Macro-viz semantic roles compiled from MosaicKit shared theme tokens."""

from __future__ import annotations

from dataclasses import dataclass

from mosaickit import DashStyle, Fill, Marker, Stroke, StyleBundle, TextStyle, Theme
from mosaickit.themes import ThemeTokens, get_tokens, list_shared_themes


@dataclass(frozen=True, slots=True)
class ThemeOptions:
    """Concrete visual options produced by the macro-viz configuration schema."""

    name: str
    background: str | None
    axis: str
    label: str
    primary: str
    secondary: str
    tertiary: str
    accent: str
    intervention: str
    muted: str
    fill_light: str
    fill_mid: str
    fill_dark: str
    fill_faint: str
    line_width: float = 2.2
    secondary_width: float = 1.6
    guide_width: float = 1.0
    marker_size: float = 36.0
    font: str = "sans"


def options_from_tokens(tokens: ThemeTokens, *, font: str = "sans") -> ThemeOptions:
    """Map shared tokens onto the visual roles used by current macro diagrams."""

    def color(role: str) -> str:
        value = tokens.color(role)
        if value is None:
            raise ValueError(f"theme role {role!r} requires a color")
        return value

    return ThemeOptions(
        name=tokens.name,
        background=tokens.color("background") or "#ffffff",
        axis=color("ink"),
        label=color("ink"),
        primary=color("primary"),
        secondary=color("secondary"),
        tertiary=color("tertiary"),
        accent=color("accent"),
        intervention=color("intervention"),
        muted=color("muted"),
        fill_light=color("fill.light"),
        fill_mid=color("fill.mid"),
        fill_dark=color("fill.dark"),
        fill_faint=color("fill.faint"),
        line_width=2.2 * tokens.line_scale,
        secondary_width=1.6 * tokens.line_scale,
        guide_width=1.0 * tokens.line_scale,
        marker_size=36.0 * tokens.marker_scale**2,
        font=font,
    )


def build_theme(options: ThemeOptions) -> Theme:
    """Build a MosaicKit theme with stable ``macro.*`` semantic roles."""
    text = TextStyle(color=options.label, size=10, font=options.font)
    roles = {
        "canvas": StyleBundle(
            fill=Fill(
                color=options.background or options.axis,
                opacity=1.0 if options.background is not None else 0.0,
            )
        ),
        "axes": StyleBundle(stroke=Stroke(color=options.axis, width=1.0), text=text),
        "title": StyleBundle(text=TextStyle(color=options.label, size=13, font=options.font)),
        "macro.accounts.component.consumption": StyleBundle(
            fill=Fill(color=options.fill_light, opacity=0.72), text=text
        ),
        "macro.accounts.component.investment": StyleBundle(
            fill=Fill(color=options.fill_mid, opacity=0.72), text=text
        ),
        "macro.accounts.component.government": StyleBundle(
            fill=Fill(color=options.fill_dark, opacity=0.72),
            text=TextStyle(color=options.label, size=10, font=options.font),
        ),
        "macro.accounts.component.net.exports": StyleBundle(
            fill=Fill(color=options.fill_faint, opacity=0.88), text=text
        ),
        "macro.accounts.component.total": StyleBundle(
            fill=Fill(color=options.primary, opacity=0.58), text=text
        ),
        "macro.series.primary": StyleBundle(
            stroke=Stroke(color=options.primary, width=options.line_width), text=text
        ),
        "macro.series.secondary": StyleBundle(
            stroke=Stroke(color=options.secondary, width=options.secondary_width), text=text
        ),
        "macro.series.tertiary": StyleBundle(
            stroke=Stroke(color=options.tertiary, width=options.secondary_width), text=text
        ),
        "macro.series.accent": StyleBundle(
            stroke=Stroke(color=options.accent, width=options.line_width), text=text
        ),
        "macro.series.trend": StyleBundle(
            stroke=Stroke(
                color=options.muted,
                width=options.secondary_width,
                dash=DashStyle.DASHED,
            ),
            text=text,
        ),
        "macro.guide": StyleBundle(
            stroke=Stroke(color=options.axis, width=options.guide_width, dash=DashStyle.DOTTED)
        ),
        "macro.recession": StyleBundle(
            fill=Fill(color=options.fill_faint, opacity=0.4), stroke=Stroke(width=0)
        ),
        "macro.gap.positive": StyleBundle(
            fill=Fill(color=options.primary, opacity=0.4), stroke=Stroke(width=0)
        ),
        "macro.gap.negative": StyleBundle(
            fill=Fill(color=options.intervention, opacity=0.4), stroke=Stroke(width=0)
        ),
        "macro.turning.peak": StyleBundle(
            marker=Marker(color=options.accent, size=options.marker_size, shape="^"), text=text
        ),
        "macro.turning.trough": StyleBundle(
            marker=Marker(color=options.secondary, size=options.marker_size, shape="v"), text=text
        ),
    }
    return Theme(options.name, roles)


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
