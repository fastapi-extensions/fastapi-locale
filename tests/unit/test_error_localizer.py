from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel, Field, ValidationError, field_validator
from pydantic_core._pydantic_core import list_all_errors

from fastapi_locale import Localization, use_locale
from fastapi_locale._catalog import BUILTIN_DIRECTORY, BUILTIN_DOMAIN
from fastapi_locale._errors_catalog import TEMPLATES, ErrorLocalizer, ErrorTemplate
from fastapi_locale._formatting import placeholders


def test_every_pydantic_error_type_has_a_template() -> None:
    missing = {error["type"] for error in list_all_errors()} - set(TEMPLATES)
    assert not missing, f"add templates for: {sorted(missing)}"


def test_template_placeholders_are_ctx_keys() -> None:
    for error in list_all_errors():
        template = TEMPLATES[error["type"]]
        ctx = set((error.get("example_context") or {}).keys())
        assert placeholders(template.message) <= ctx, template.type
        if template.plural is not None:
            assert template.count_key in ctx, template.type


def test_template_file_is_in_sync() -> None:
    template = (BUILTIN_DIRECTORY / f"{BUILTIN_DOMAIN}.pot").read_text(encoding="utf-8")
    for error_type in TEMPLATES:
        assert f'msgctxt "{error_type}"' in template, error_type


class Order(BaseModel):
    quantity: int = Field(gt=0)
    code: str = Field(min_length=3)
    note: str = ""

    @field_validator("note")
    @classmethod
    def no_spam(cls, value: str) -> str:
        if "spam" in value:
            msg = "spam is not allowed"
            raise ValueError(msg)
        return value


def errors(**data: object) -> list[dict[str, object]]:
    with pytest.raises(ValidationError) as info:
        Order(**data)
    return [dict(error) for error in info.value.errors()]


@pytest.fixture
def localizer(localization: Localization) -> ErrorLocalizer:
    localization.make_default()
    return ErrorLocalizer()


def test_english_matches_pydantic(localizer: ErrorLocalizer, localization: Localization) -> None:
    raw = errors(quantity=0, code="a", note="spam")
    localized = localizer.localize(raw, localization.translator("en"))
    assert [e["msg"] for e in localized] == [e["msg"] for e in raw]


def test_only_msg_changes(localizer: ErrorLocalizer, localization: Localization) -> None:
    raw = errors(quantity=0, code="ab")
    localized = localizer.localize(raw, localization.translator("de"))
    assert localized[0]["msg"] == "Wert muss groesser als 0 sein (App)"
    for before, after in zip(raw, localized, strict=True):
        assert {k: v for k, v in before.items() if k != "msg"} == {
            k: v for k, v in after.items() if k != "msg"
        }


def test_plural_uses_count_key(localization: Localization) -> None:
    localization.make_default()
    template = ErrorTemplate("t", "{n} one {c}", plural="{n} many {c}", count_key="c")
    localizer = ErrorLocalizer({"t": template})
    with use_locale("en") as translator:
        one, many, missing = localizer.localize(
            [
                {"type": "t", "msg": "x", "ctx": {"c": 1}},
                {"type": "t", "msg": "x", "ctx": {"c": 2}},
                {"type": "t", "msg": "x"},
            ],
            translator,
        )
    assert one["msg"] == "1 one 1"
    assert many["msg"] == "2 many 2"
    assert missing["msg"] == "{n} one {c}"


def test_unknown_types_keep_the_pydantic_message(
    localizer: ErrorLocalizer, localization: Localization
) -> None:
    error = {"type": "my_custom_error", "msg": "Custom text", "loc": ("a",)}
    assert localizer.localize([error], localization.translator("de")) == [error]


def test_value_error_keeps_the_application_text(
    localizer: ErrorLocalizer, localization: Localization
) -> None:
    raw = errors(quantity=1, code="abc", note="spam")
    assert localizer.localize(raw, localization.translator("en"))[0]["msg"] == (
        "Value error, spam is not allowed"
    )


def test_builtin_directory_exists() -> None:
    assert Path(BUILTIN_DIRECTORY / f"{BUILTIN_DOMAIN}.pot").is_file()
