"""The ``[macro.*]`` schema for the shared ``econ-viz.toml`` file."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, cast

from mosaickit import Config as MosaicConfig
from mosaickit import MathFont, TextFonts, econ_toml
from mosaickit.themes import get_tokens

from macro_viz.themes import ThemeOptions, build_theme, list_themes, options_from_tokens


@dataclass(frozen=True, slots=True)
class _Colors:
    background: str | None = None
    axis: str | None = None
    label: str | None = None
    primary: str | None = None
    secondary: str | None = None
    tertiary: str | None = None
    accent: str | None = None
    intervention: str | None = None
    muted: str | None = None


@dataclass(frozen=True, slots=True)
class _Draft:
    base: str
    palette: str | None = None
    font: str = "sans"
    fonts: TextFonts | None = None
    math_font: MathFont | None = None
    colors: _Colors = field(default_factory=_Colors)
    line_width: float | None = None
    secondary_width: float | None = None
    guide_width: float | None = None
    marker_size: float | None = None


@dataclass(frozen=True, slots=True)
class Settings:
    """Resolved macro-viz settings and their MosaicKit configuration."""

    options: ThemeOptions
    fonts: TextFonts | None = None
    math_font: MathFont | None = None

    @property
    def theme(self):  # type: ignore[no-untyped-def]
        """Resolved MosaicKit theme."""
        return build_theme(self.options)

    def mosaickit_config(self) -> MosaicConfig:
        """Configuration passed to every MosaicKit canvas."""
        return MosaicConfig(theme=self.theme, fonts=self.fonts, math_font=self.math_font)


def _base(name: str):  # type: ignore[no-untyped-def]
    return lambda: _Draft(base=name)


def _palette(value: Any, ctx: econ_toml.Context) -> str:
    return str(econ_toml.choice("palette", list_themes()).convert(value, ctx, "palette"))


def _math_font(value: Any, ctx: econ_toml.Context) -> MathFont:
    return MathFont(Path(value))


def _finish(draft: _Draft, ctx: econ_toml.Context) -> Settings:
    del ctx
    tokens = get_tokens(draft.palette or draft.base)
    options = options_from_tokens(tokens, font=draft.font)
    options = replace(
        options,
        background=draft.colors.background or options.background,
        axis=draft.colors.axis or options.axis,
        label=draft.colors.label or options.label,
        primary=draft.colors.primary or options.primary,
        secondary=draft.colors.secondary or options.secondary,
        tertiary=draft.colors.tertiary or options.tertiary,
        accent=draft.colors.accent or options.accent,
        intervention=draft.colors.intervention or options.intervention,
        muted=draft.colors.muted or options.muted,
        line_width=draft.line_width or options.line_width,
        secondary_width=draft.secondary_width or options.secondary_width,
        guide_width=draft.guide_width or options.guide_width,
        marker_size=(
            draft.marker_size**2 if draft.marker_size is not None else options.marker_size
        ),
    )
    return Settings(options=options, fonts=draft.fonts, math_font=draft.math_font)


_BASES = {name: _base(name) for name in list_themes()}
_COLOR_FIELDS = (
    "background",
    "axis",
    "label",
    "primary",
    "secondary",
    "tertiary",
    "accent",
    "intervention",
    "muted",
)

SCHEMA = econ_toml.register(
    econ_toml.Schema(
        package="macro",
        base=_BASES,
        fields={
            "palette": econ_toml.transform("palette", _palette),
            **{f"color.{name}": econ_toml.color(f"colors.{name}") for name in _COLOR_FIELDS},
            "stroke.series": econ_toml.positive("line_width"),
            "stroke.secondary": econ_toml.positive("secondary_width"),
            "stroke.guide": econ_toml.positive("guide_width"),
            "marker.turning_point": econ_toml.positive("marker_size"),
        },
        shared={
            "font": "font",
            "fonts": "fonts",
            "math_font": econ_toml.transform("math_font", _math_font),
            "background": "colors.background",
            "axis": "colors.axis",
            "label": "colors.label",
        },
        finalize=_finish,
        docs={
            "palette": "shared colour theme for macro-viz only",
            **{f"color.{name}": "unset keeps the shared theme colour" for name in _COLOR_FIELDS},
            "stroke.series": "primary series width in points",
            "stroke.secondary": "secondary series width in points",
            "stroke.guide": "guide width in points",
            "marker.turning_point": "turning-point marker area in points squared",
        },
    )
)


class Config(SCHEMA.config_class()):  # type: ignore[misc]
    """Settings loaded exclusively through the MosaicKit schema machinery."""

    __slots__ = ()

    @property
    def settings(self) -> Settings:
        return cast(Settings, self.value)

    @property
    def theme(self):  # type: ignore[no-untyped-def]
        return self.settings.theme

    def mosaickit_config(self) -> MosaicConfig:
        return self.settings.mosaickit_config()


def active_config() -> Config:
    """The active configuration, or the built-in manual defaults."""
    active = Config.active()
    return active if active is not None else Config()


__all__ = ["SCHEMA", "Config", "Settings", "active_config"]
