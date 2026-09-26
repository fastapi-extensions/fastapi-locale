from __future__ import annotations

import pytest

from fastapi_locale._formatting import format_message, placeholders


@pytest.mark.parametrize(
    ("template", "params", "expected"),
    [
        ("Hello {name}", {"name": "Asha"}, "Hello Asha"),
        ("{b} before {a}", {"a": 1, "b": 2}, "2 before 1"),
        ("{{literal}} {x}", {"x": "y"}, "{literal} y"),
        ("no placeholders", {"x": 1}, "no placeholders"),
        ("{_private1}", {"_private1": "ok"}, "ok"),
        ("{class}", {"class": "Model"}, "Model"),
    ],
)
def test_substitutes_named_values(template: str, params: dict[str, object], expected: str) -> None:
    assert format_message(template, params) == expected


@pytest.mark.parametrize(
    "template",
    ["{obj.__class__}", "{items[0]}", "{0}", "{}", "{x!r}", "{x:>10}", "{ x }"],
)
def test_only_plain_names_are_substituted(template: str) -> None:
    assert format_message(template, {"obj": object(), "items": [1], "x": 1}) == template


def test_missing_values_are_left_and_reported() -> None:
    missing: list[str] = []
    assert format_message("Hi {name}", {}, missing.append) == "Hi {name}"
    assert missing == ["name"]


def test_missing_values_without_callback() -> None:
    assert format_message("Hi {name}", {"other": 1}) == "Hi {name}"


def test_placeholders() -> None:
    assert placeholders("{a} {{b}} {c} {a}") == frozenset({"a", "c"})
