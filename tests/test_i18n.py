from __future__ import annotations

from collections.abc import Iterator

import pytest

from macro_viz import Config, ValidationError
from macro_viz.i18n import LANGUAGES, Labels, label_ids, label_table, text, validate_language


@pytest.fixture(autouse=True)
def _reset_config() -> Iterator[None]:
    yield
    Config.reset()


def test_every_language_has_the_same_label_ids() -> None:
    reference = set(label_table("en"))

    assert all(set(label_table(language)) == reference for language in LANGUAGES)
    assert all(label_table(language)[key] for language in LANGUAGES for key in reference)
    assert set(label_ids()) == reference


def test_text_looks_up_ids_per_language_and_rejects_unknown_ones() -> None:
    assert text("keynesian.mark.autonomous", language="en") == "Autonomous spending"
    assert text("keynesian.mark.autonomous", language="zh-TW") == "自發性支出"
    assert text("keynesian.mark.autonomous", language="zh-CN") == "自发性支出"
    with pytest.raises(ValidationError):
        text("no.such.id", language="en")
    with pytest.raises(ValidationError):
        validate_language("fr")


def test_math_labels_keep_their_braces_without_fields() -> None:
    assert Labels({"keynesian.mark.shift": "$\\bar{A}$"})("keynesian.mark.shift") == "$\\bar{A}$"


def test_the_configured_language_selects_the_text() -> None:
    english = Labels()("keynesian.mark.autonomous")
    Config.from_dict({"macro": {"language": "zh-TW"}}).use()
    chinese = Labels()("keynesian.mark.autonomous")
    explicit = Labels(language="en")("keynesian.mark.autonomous")

    assert english == "Autonomous spending"
    assert chinese == "自發性支出"
    assert explicit == english


def test_overrides_replace_text_and_unknown_ids_raise() -> None:
    assert Labels({"keynesian.mark.degrees": "P"})("keynesian.mark.degrees") == "P"
    with pytest.raises(ValidationError):
        Labels({"no.such.label": "x"})
