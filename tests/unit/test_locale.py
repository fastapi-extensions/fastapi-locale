from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from fastapi_locale import Locale
from fastapi_locale._locale import MAX_TAG_LENGTH


@pytest.mark.parametrize(
    ("value", "tag", "language", "script", "region"),
    [
        ("en", "en", "en", None, None),
        ("EN", "en", "en", None, None),
        ("pt_br", "pt-BR", "pt", None, "BR"),
        ("pt-BR", "pt-BR", "pt", None, "BR"),
        ("zh_hant_tw", "zh-Hant-TW", "zh", "Hant", "TW"),
        ("sr-Latn", "sr-Latn", "sr", "Latn", None),
        ("es-419", "es-419", "es", None, "419"),
        ("de-CH-1996", "de-CH-1996", "de", None, "CH"),
        ("  hi-IN  ", "hi-IN", "hi", None, "IN"),
        ("fil", "fil", "fil", None, None),
    ],
)
def test_parse_normalizes(
    value: str, tag: str, language: str, script: str | None, region: str | None
) -> None:
    locale = Locale.parse(value)
    assert (locale.tag, locale.language, locale.script, locale.region) == (
        tag,
        language,
        script,
        region,
    )
    assert str(locale) == tag


@pytest.mark.parametrize(
    "value",
    ["", "e", "abcdefghi", "en..US", "en_US.UTF-8", "../etc", "en/US", "C", "12", "abcd"],
)
def test_invalid_tags_are_rejected(value: str) -> None:
    assert Locale.try_parse(value) is None
    with pytest.raises(ValueError, match="not a valid language tag"):
        Locale.parse(value)


def test_overlong_input_is_rejected_before_parsing() -> None:
    assert Locale.try_parse("en-" + "a" * MAX_TAG_LENGTH) is None


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        ("en", ["en"]),
        ("pt-BR", ["pt-BR", "pt"]),
        ("zh-Hant-TW", ["zh-Hant-TW", "zh-Hant", "zh"]),
        ("en-a-bbb-x-ccc", ["en-a-bbb-x-ccc", "en-a-bbb", "en"]),
    ],
)
def test_truncations_follow_rfc_4647(tag: str, expected: list[str]) -> None:
    assert [locale.tag for locale in Locale.parse(tag).truncations()] == expected


@pytest.mark.parametrize(
    ("tag", "direction"), [("ar", "rtl"), ("he", "rtl"), ("en", "ltr"), ("qqq", "ltr")]
)
def test_text_direction(tag: str, direction: str) -> None:
    assert Locale.parse(tag).text_direction == direction


def test_locales_compare_by_value() -> None:
    assert Locale.parse("pt_br") == Locale.parse("PT-BR")
    assert len({Locale.parse("hi"), Locale.parse("HI")}) == 1


@given(st.text(max_size=80))
def test_try_parse_never_raises(value: str) -> None:
    Locale.try_parse(value)


@given(
    st.from_regex(r"[a-z]{2,3}(-[A-Z][a-z]{3})?(-[A-Z]{2})?", fullmatch=True),
)
def test_parse_is_idempotent(value: str) -> None:
    locale = Locale.parse(value)
    assert Locale.parse(str(locale)) == locale
