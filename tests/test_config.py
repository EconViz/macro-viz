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

    assert Config.from_dict({}) == config
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
                "stroke": {"curve": 3.5, "arrow": 2},
                "marker": {"point": 7},
            },
        }
    )

    assert config.theme.name == "nord"
    assert config.settings.options.primary == "#123456"
    assert config.settings.options.curve_width == 3.5
    assert config.settings.options.arrow_width == 2
    assert config.settings.options.point_size == 49
    assert config.settings.options.background == Config().settings.options.background


@pytest.mark.parametrize(
    "data",
    [
        {"macro": {"palette": "rainbow"}},
        {"macro": {"stroke": {"curve": 0}}},
        {"macro": {"marker": {"point": -1}}},
        {"macro": {"unknown": True}},
    ],
)
def test_invalid_macro_settings_are_rejected(data: dict[str, object]) -> None:
    with pytest.raises(ConfigurationError):
        Config.from_dict(data)


def test_schema_is_registered_under_macro_table() -> None:
    assert econ_toml.registered()["macro"] is SCHEMA
    assert "# [macro.stroke]" in SCHEMA.template()


def test_language_and_label_nudges_are_validated_and_resolved() -> None:
    config = Config.from_dict(
        {"macro": {"language": "zh-CN", "label": {"point": {"top": "2pt"}}, "text": {"scale": 1.5}}}
    )

    assert config.settings.language == "zh-CN"
    assert config.settings.options.text_scale == 1.5
    assert set(config.settings.label_nudges) == {"point"}
    with pytest.raises(ConfigurationError):
        Config.from_dict({"macro": {"language": "fr"}})
    with pytest.raises(ConfigurationError):
        Config.from_dict({"macro": {"label": {"curve": {"top": "1em"}}}})


def test_output_without_settings_equals_the_empty_settings_output() -> None:
    from macro_viz.keynesian import ConsumptionFunction, KeynesianCross
    from macro_viz.visuals import keynesian_cross_canvas

    model = KeynesianCross(ConsumptionFunction(20, 0.6), 20, 30, 20)

    Config.reset()
    without = keynesian_cross_canvas(model, title="T").snapshot()
    Config.from_dict({}).use()
    empty = keynesian_cross_canvas(model, title="T").snapshot()

    assert without == empty
