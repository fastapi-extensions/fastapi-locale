from __future__ import annotations

import copy

import pytest

from fastapi_locale import Localization, Translator
from fastapi_locale._catalog import BUILTIN_DOMAIN
from fastapi_locale._openapi import translate_schema

SCHEMA = {
    "info": {"title": "Orders API", "description": "Hello", "version": "1.0"},
    "paths": {
        "/items": {
            "get": {
                "summary": "Item",
                "responses": {
                    "200": {"description": "Successful Response"},
                    "422": {"description": "Validation Error"},
                },
            }
        }
    },
    "components": {
        "schemas": {
            "Item": {
                "title": "Item",
                "properties": {
                    "title": {"type": "string", "title": "Hello", "default": {"title": "Hello"}},
                    "kind": {"enum": ["Hello"], "examples": ["Hello"], "const": "Hello"},
                },
            }
        }
    },
    "tags": [{"name": "Hello", "description": "Not translated at all"}],
}


@pytest.fixture
def german(localization: Localization) -> Translator:
    return localization.translator("de")


def test_text_keys_are_translated(german: Translator) -> None:
    result = translate_schema(SCHEMA, german, BUILTIN_DOMAIN)
    assert result["info"] == {"title": "Bestell-API", "description": "Hallo", "version": "1.0"}
    operation = result["paths"]["/items"]["get"]
    assert operation["summary"] == "Artikel (Schema)"
    assert operation["responses"]["200"]["description"] == "Erfolgreiche Antwort"
    assert operation["responses"]["422"]["description"] == "Validierungsfehler"
    assert result["tags"] == [{"name": "Hello", "description": "Not translated at all"}]


def test_names_and_data_are_left_alone(german: Translator) -> None:
    item = translate_schema(SCHEMA, german, BUILTIN_DOMAIN)["components"]["schemas"]["Item"]
    assert item["title"] == "Artikel (Schema)"
    assert set(item["properties"]) == {"title", "kind"}
    assert item["properties"]["title"]["title"] == "Hallo"
    assert item["properties"]["title"]["default"] == {"title": "Hello"}
    kind = {"enum": ["Hello"], "examples": ["Hello"], "const": "Hello"}
    assert item["properties"]["kind"] == kind


def test_input_is_not_changed(german: Translator) -> None:
    before = copy.deepcopy(SCHEMA)
    translate_schema(SCHEMA, german, BUILTIN_DOMAIN)
    assert before == SCHEMA


def test_source_language_is_unchanged(localization: Localization) -> None:
    english = localization.translator("en")
    assert translate_schema(SCHEMA, english, BUILTIN_DOMAIN) == SCHEMA
