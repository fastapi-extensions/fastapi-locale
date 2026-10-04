from __future__ import annotations

from pathlib import Path
from typing import Annotated

import pytest
from babel.messages.pofile import read_po
from pydantic import BaseModel, Field, TypeAdapter, ValidationError, field_validator
from pydantic_core._pydantic_core import list_all_errors

from fastapi_locale import Localization
from fastapi_locale._catalog import BUILTIN_DIRECTORY, BUILTIN_DOMAIN
from fastapi_locale._errors_catalog import TEMPLATES, ErrorLocalizer, all_templates
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
    with (BUILTIN_DIRECTORY / f"{BUILTIN_DOMAIN}.pot").open("rb") as stream:
        entries = {(message.context, message.id) for message in read_po(stream)}
    for template in all_templates():
        msgid = template.message if template.plural is None else (template.message, template.plural)
        assert (template.type, msgid) in entries, template.message


def test_builtin_catalogs_translate_every_template() -> None:
    paths = sorted(BUILTIN_DIRECTORY.glob(f"*/LC_MESSAGES/{BUILTIN_DOMAIN}.po"))
    assert len(paths) >= 5
    for path in paths:
        with path.open("rb") as stream:
            catalog = read_po(stream, locale=path.parent.parent.name)
        for template in all_templates():
            message = catalog.get(template.message, context=template.type)
            assert message is not None, template.message
            strings = message.string if isinstance(message.string, tuple) else (message.string,)
            assert all(strings), f"{path.parent.parent.name}: {template.message}"


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


def too_short(minimum: int, actual: int) -> dict[str, object]:
    return {
        "type": "too_short",
        "msg": "original",
        "ctx": {"field_type": "List", "min_length": minimum, "actual_length": actual},
    }


def test_plural_uses_count_key(localizer: ErrorLocalizer, localization: Localization) -> None:
    one, many = localizer.localize(
        [too_short(1, 0), too_short(2, 1)], localization.translator("fr")
    )
    assert one["msg"] == "List doit contenir au moins 1 élément après validation, et non 0"
    assert many["msg"] == "List doit contenir au moins 2 éléments après validation, et non 1"


def test_source_language_keeps_the_original_message(
    localizer: ErrorLocalizer, localization: Localization
) -> None:
    errors_: list[dict[str, object]] = [
        too_short(2, 1),
        {"type": "json_invalid", "msg": "JSON decode error", "ctx": {"error": "Expecting value"}},
    ]
    for tag in ("en", "ja"):  # the source language, and a locale without a catalog
        assert localizer.localize(errors_, localization.translator(tag)) == errors_


def test_errors_without_the_values_a_template_needs_keep_the_original_message(
    localizer: ErrorLocalizer, localization: Localization
) -> None:
    incomplete: list[dict[str, object]] = [
        {"type": "greater_than", "msg": "Input should be greater than 5"},
        {"type": "too_short", "msg": "original", "ctx": {"min_length": 1}},
        {"type": "greater_than", "msg": "original", "ctx": {"gt": None}},
        {"msg": "no type at all"},
    ]
    assert localizer.localize(incomplete, localization.translator("fr")) == incomplete


def test_unknown_length_uses_the_open_ended_message(
    localizer: ErrorLocalizer, localization: Localization
) -> None:
    error = {
        "type": "too_long",
        "msg": "Set should have at most 3 items after validation, not more",
        "ctx": {"field_type": "Set", "max_length": 3, "actual_length": None},
    }
    french = localizer.localize([error], localization.translator("fr"))[0]["msg"]
    assert french == "Set doit contenir au plus 3 éléments après validation, pas plus"


@pytest.mark.parametrize(
    ("bound", "shown"),
    [(0, "0"), (2.0, "2"), (0.5, "0.5"), (1e16, "10000000000000000"), (1e-7, "0.0000001")],
)
def test_numbers_are_shown_as_pydantic_shows_them(
    localizer: ErrorLocalizer, localization: Localization, bound: float, shown: str
) -> None:
    with pytest.raises(ValidationError) as info:
        TypeAdapter(Annotated[float, Field(gt=bound)]).validate_python(-1)
    raw = info.value.errors(include_url=False)
    assert raw[0]["msg"] == f"Input should be greater than {shown}"
    french = localizer.localize(raw, localization.translator("fr"))[0]["msg"]
    assert french == f"L'entrée doit être supérieure à {shown}"


def test_a_count_that_is_not_an_integer_uses_the_form_for_one(
    localizer: ErrorLocalizer, localization: Localization
) -> None:
    error = too_short(2, 1)
    error["ctx"] = {**error["ctx"], "min_length": "2"}  # type: ignore[dict-item]
    french = localizer.localize([error], localization.translator("fr"))[0]["msg"]
    assert french == "List doit contenir au moins 2 élément après validation, et non 1"


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
