"""The ``[macro.*]`` schema for the shared ``econ-viz.toml`` file.

mosaickit reads and checks the file (see ``mosaickit.econ_toml``); this module only
declares what macro-viz takes from it. The shared top level sets the starting colour model
(``base``), the fonts and the axis and label colours; macro-viz's own settings live in the
``[macro]`` table::

    base = "manual"           # shared theme to start from (mosaickit.themes)

    [font]
    text = "serif"
    math = "fonts/texgyrepagella-math.otf"

    [fonts]
    serif = ["fonts/texgyrepagella-regular.otf", "fonts/texgyrepagella-italic.otf"]

    [macro]
    palette = "manual"        # colour model for macro-viz only; wins over base
    language = "zh-TW"        # language of built-in figure text

    [macro.color]             # any colour role
    primary = "blue"

    [macro.stroke]            # line widths in points
    curve = 3.5

    [macro.marker]
    point = 6.5               # equilibrium dot diameter in points

    [macro.text]
    scale = 1.5               # multiplies every text size

    [macro.label.point]       # move whole groups of labels (see macro_viz.label_groups)
    top = "2pt"               # also bottom, left, right; pt, mm, cm or in, no em

Load it once and every figure uses it::

    from macro_viz import Config
    Config.load("econ-viz.toml").use()

Relative paths are resolved against the file's directory. Anything left out keeps the
built-in default.
"""

from __future__ import annotations

from dataclasses import dataclass, field, make_dataclass, replace
from pathlib import Path
from typing import Any, cast

from mosaickit import Config as MosaicConfig
from mosaickit import MathFont, TextFonts, econ_toml
from mosaickit.styles.nudge import Nudge, nudge_from
from mosaickit.themes import get_tokens

from macro_viz.i18n import DEFAULT_LANGUAGE, LANGUAGES
from macro_viz.label_groups import LABEL_GROUPS, LABEL_SIDES
from macro_viz.themes import ThemeOptions, build_theme, list_themes, options_from_tokens

_DIRECTIONS = {"top": "up", "bottom": "down", "left": "left", "right": "right"}
_COLOR_FIELDS = (
    "background",
    "axis",
    "label",
    "primary",
    "secondary",
    "tertiary",
)
_STROKES = {
    "curve": "curve_width",
    "shifted": "shifted_width",
    "arrow": "arrow_width",
    "guide": "guide_width",
}

_Colors = make_dataclass(
    "_Colors",
    [(name, "str | None", field(default=None)) for name in _COLOR_FIELDS],
    frozen=True,
    slots=True,
)
_Nudges = make_dataclass(
    "_Nudges",
    [
        (f"{group}_{side}", "float | None", field(default=None))
        for group in LABEL_GROUPS
        for side in LABEL_SIDES
    ],
    frozen=True,
    slots=True,
)
_Sizes = make_dataclass(
    "_Sizes",
    [
        *((option, "float | None", field(default=None)) for option in _STROKES.values()),
        ("point_diameter", "float | None", field(default=None)),
        ("text_scale", "float | None", field(default=None)),
    ],
    frozen=True,
    slots=True,
)


@dataclass(frozen=True, slots=True)
class _Draft:
    base: str
    palette: str | None = None
    language: str = DEFAULT_LANGUAGE
    font: str = "sans"
    fonts: TextFonts | None = None
    math_font: MathFont | None = None
    colors: Any = field(default_factory=_Colors)
    sizes: Any = field(default_factory=_Sizes)
    nudges: Any = field(default_factory=_Nudges)


@dataclass(frozen=True, slots=True)
class Settings:
    """Resolved macro-viz settings and their MosaicKit configuration."""

    options: ThemeOptions
    fonts: TextFonts | None = None
    math_font: MathFont | None = None
    language: str = DEFAULT_LANGUAGE
    label_nudges: dict[str, Nudge] = field(default_factory=dict, hash=False)

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


def _label_nudges(nudges: Any) -> dict[str, Nudge]:
    """The nudge of each group the file moves; a group set to no move is left out."""
    found: dict[str, Nudge] = {}
    for group in LABEL_GROUPS:
        nudge = nudge_from(**{side: getattr(nudges, f"{group}_{side}") for side in LABEL_SIDES})
        if not nudge.is_zero:
            found[group] = nudge
    return found


def _finish(draft: _Draft, ctx: econ_toml.Context) -> Settings:
    del ctx
    tokens = get_tokens(draft.palette or draft.base)
    options = options_from_tokens(tokens, font=draft.font)
    colors = {
        name: value for name in _COLOR_FIELDS if (value := getattr(draft.colors, name)) is not None
    }
    sizes = {
        option: value
        for option in (*_STROKES.values(), "text_scale")
        if (value := getattr(draft.sizes, option)) is not None
    }
    if draft.sizes.point_diameter is not None:
        sizes["point_size"] = draft.sizes.point_diameter**2
    options = replace(options, **colors, **sizes)
    return Settings(
        options=options,
        fonts=draft.fonts,
        math_font=draft.math_font,
        language=draft.language,
        label_nudges=_label_nudges(draft.nudges),
    )


_BASES = {name: _base(name) for name in list_themes()}

SCHEMA = econ_toml.register(
    econ_toml.Schema(
        package="macro",
        base=_BASES,
        fields={
            "palette": econ_toml.transform("palette", _palette),
            "language": econ_toml.choice("language", LANGUAGES),
            **{f"color.{name}": econ_toml.color(f"colors.{name}") for name in _COLOR_FIELDS},
            **{
                f"stroke.{name}": econ_toml.positive(f"sizes.{option}")
                for name, option in _STROKES.items()
            },
            "marker.point": econ_toml.positive("sizes.point_diameter"),
            "text.scale": econ_toml.positive("sizes.text_scale"),
            **{
                f"label.{group}.{side}": econ_toml.length(f"nudges.{group}_{side}")
                for group in LABEL_GROUPS
                for side in LABEL_SIDES
            },
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
            "palette": "shared colour theme for macro-viz only; wins over base",
            "language": "language of built-in figure text (en, zh-TW, zh-CN)",
            **{f"color.{name}": "unset keeps the shared theme colour" for name in _COLOR_FIELDS},
            "stroke.curve": "theory curve width in points (default 3.5)",
            "stroke.shifted": "old, shifted-from curve width in points (default 1.0)",
            "stroke.arrow": "movement arrow width in points (default 1.0)",
            "stroke.guide": "guide width in points (default 1.0)",
            "marker.point": "equilibrium dot diameter in points (default 6.5)",
            "text.scale": "multiplies every text size (default 1.0)",
            **{
                f"label.{group}.{side}": f"move {group} labels {_DIRECTIONS[side]} (a length)"
                for group in LABEL_GROUPS
                for side in LABEL_SIDES
            },
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
    """The active configuration, or the built-in colored defaults."""
    active = Config.active()
    return active if active is not None else Config()


__all__ = ["SCHEMA", "Config", "Settings", "active_config"]
