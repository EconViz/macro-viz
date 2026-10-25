"""Built-in figure text in English, Traditional Chinese, or Simplified Chinese.

Every word macro-viz puts in a figure or gives to a derived series is looked up here by a
stable id in ``locale/labels.json`` (``"axis.date"``, ``"label.peak"``, ...). Text you pass
yourself (``title=``, axis names, series names) is never translated. The language is the
``language`` setting of the ``[macro]`` table of ``econ-viz.toml``; the default is ``"en"``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from functools import cache
from importlib import resources

from macro_viz.errors import ValidationError

LANGUAGES = ("en", "zh-TW", "zh-CN")
DEFAULT_LANGUAGE = LANGUAGES[0]


def validate_language(language: str) -> str:
    """Return ``language`` if macro-viz can draw it, else raise ``ValidationError``."""
    if language not in LANGUAGES:
        raise ValidationError(f"language must be one of {', '.join(LANGUAGES)}; got {language!r}")
    return language


@cache
def label_table(language: str) -> Mapping[str, str]:
    """Label id mapped to its text in ``language``."""
    validate_language(language)
    source = resources.files("macro_viz.locale").joinpath("labels.json").read_text("utf-8")
    table: dict[str, str] = json.loads(source)[language]
    return table


def label_ids() -> tuple[str, ...]:
    """The ids of every built-in label."""
    return tuple(label_table(DEFAULT_LANGUAGE))


def text(label_id: str, *, language: str | None = None, **fields: str) -> str:
    """The built-in text with id ``label_id``; ``fields`` fill ``{name}`` placeholders.

    ``language`` defaults to the active configuration's language.
    """
    if language is None:
        from macro_viz.config import active_config

        language = active_config().settings.language
    table = label_table(validate_language(language))
    if label_id not in table:
        raise ValidationError(f"unknown label id {label_id!r}")
    return table[label_id].format(**fields) if fields else table[label_id]


class Labels:
    """The built-in text of one figure: ids resolved in one language, with caller overrides.

    ``overrides`` maps label ids to the text to draw instead; an unknown id raises. Calling the
    object with an id returns its text.
    """

    def __init__(self, overrides: Mapping[str, str] | None = None, *, language: str | None = None):
        self._language = language
        self._overrides = dict(overrides or {})
        unknown = sorted(set(self._overrides) - set(label_ids()))
        if unknown:
            raise ValidationError(f"unknown label ids: {', '.join(unknown)}")

    def __call__(self, label_id: str, **fields: str) -> str:
        if label_id in self._overrides:
            override = self._overrides[label_id]
            return override.format(**fields) if fields else override
        return text(label_id, language=self._language, **fields)


__all__ = [
    "DEFAULT_LANGUAGE",
    "LANGUAGES",
    "Labels",
    "label_ids",
    "label_table",
    "text",
    "validate_language",
]
