from __future__ import annotations

from collections.abc import Iterator

import pytest
from mosaickit import ConfigurationError, econ_toml

from macro_viz import Config
from macro_viz.config import SCHEMA


@pytest.fixture(autouse=True)
def _reset_config() -> Iterator[None]:
    yield
    Config.reset()


def test_package_default_is_colored_on_white() -> None:
    config = Config()

    assert config.theme.name == "default"
    assert config.settings.options.background == "#ffffff"
    assert config.settings.options.primary != config.settings.options.secondary


def test_manual_theme_is_an_explicit_monochrome_choice() -> None:
    config = Config.from_dict({"base": "manual"})

    assert config.theme.name == "manual"
    assert config.settings.options.background == "#ffffff"
    assert config.settings.options.primary == "#8c8c8c"


def test_macro_table_overrides_palette_strokes_and_colors() -> None:
    config = Config.from_dict(
        {
            "base": "default",
            "macro": {
                "palette": "nord",
                "color": {"primary": "#123456"},
                "stroke": {"series": 3.5},
                "marker": {"turning_point": 7},
            },
        }
    )

    assert config.theme.name == "nord"
    assert config.settings.options.primary == "#123456"
    assert config.settings.options.line_width == 3.5
    assert config.settings.options.marker_size == 49
    assert config.settings.options.background == "#ffffff"


@pytest.mark.parametrize(
    "data",
    [
        {"macro": {"palette": "rainbow"}},
        {"macro": {"stroke": {"series": 0}}},
        {"macro": {"marker": {"turning_point": -1}}},
        {"macro": {"unknown": True}},
    ],
)
def test_invalid_macro_settings_are_rejected(data: dict[str, object]) -> None:
    with pytest.raises(ConfigurationError):
        Config.from_dict(data)


def test_schema_is_registered_under_macro_table() -> None:
    assert econ_toml.registered()["macro"] is SCHEMA
    assert "# [macro.stroke]" in SCHEMA.template()
