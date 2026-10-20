import json
from pathlib import Path

import pytest

LOCALES = Path(__file__).resolve().parents[1] / "src" / "cleartake" / "web" / "locales"
OTHERS = ["zh-TW", "zh-CN", "ja", "ko", "es", "fr", "de", "pt-BR"]


def load(code):
    return json.loads((LOCALES / f"{code}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("code", OTHERS)
def test_locale_matches_english_keys(code):
    english, other = load("en"), load(code)
    optional = {key for key in english if key.endswith(".one")}  # plural forms only some languages need
    assert set(other) - optional == set(english) - optional
    assert all(value.strip() for value in other.values())


@pytest.mark.parametrize("code", OTHERS)
def test_locale_keeps_placeholders(code):
    english, other = load("en"), load(code)
    for key, value in english.items():
        for name in ("{n}", "{x}", "{pct}", "{name}", "{eta}"):
            if name in value:
                assert name in other[key], f"{code}:{key} lost {name}"
