"""Translation of a generated OpenAPI schema into one locale (ADR-0009)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi_locale._translator import Translator

__all__ = ["OPENAPI_CONTEXT", "OPENAPI_MESSAGES", "translate_schema"]

# Message context that lets translators word API documentation apart from UI text.
OPENAPI_CONTEXT = "openapi"

# English text FastAPI itself puts into every schema; translated by the built-in catalog.
OPENAPI_MESSAGES = (
    "Successful Response",
    "Validation Error",
    "Detail",
    "Location",
    "Message",
    "Error Type",
    "Input",
    "Context",
)

_TEXT_KEYS = frozenset({"title", "summary", "description"})
# Values under these keys are application data, never documentation text.
_DATA_KEYS = frozenset({"default", "example", "const", "enum"})
# The keys of these objects are names chosen by the application (properties, response codes,
# component names), so a property called "default" or "title" is not read as a keyword.
_NAME_MAPS = frozenset(
    {
        "$defs",
        "callbacks",
        "definitions",
        "dependentSchemas",
        "encoding",
        "headers",
        "links",
        "mapping",
        "parameters",
        "pathItems",
        "paths",
        "patternProperties",
        "properties",
        "requestBodies",
        "responses",
        "schemas",
        "securitySchemes",
        "variables",
        "webhooks",
    }
)


def translate_schema(
    schema: Mapping[str, Any], translator: Translator, builtin_domain: str
) -> dict[str, Any]:
    """Return a copy of ``schema`` with titles, summaries and descriptions translated."""
    cache: dict[str, str] = {}

    def text(value: Any) -> Any:  # noqa: ANN401 - JSON values of any type
        if not isinstance(value, str):
            return value
        if value not in cache:
            cache[value] = _translate(value, translator, builtin_domain)
        return cache[value]

    def named(node: Mapping[str, Any]) -> dict[str, Any]:
        return {name: walk(value) for name, value in node.items()}

    def examples(node: Any) -> Any:  # noqa: ANN401 - JSON values of any type
        # A list holds example values. A mapping holds OpenAPI Example Objects, whose summary
        # and description are documentation while their value is data.
        if not isinstance(node, Mapping):
            return node
        return {
            name: {
                key: text(value) if key in _TEXT_KEYS else value for key, value in example.items()
            }
            if isinstance(example, Mapping)
            else example
            for name, example in node.items()
        }

    def walk(node: Any) -> Any:  # noqa: ANN401 - JSON values of any type
        if isinstance(node, list):
            return [walk(item) for item in node]
        if not isinstance(node, Mapping):
            return node
        result: dict[str, Any] = {}
        for key, value in node.items():
            if key in _DATA_KEYS or (isinstance(key, str) and key.startswith("x-")):
                result[key] = value
            elif key in _TEXT_KEYS and isinstance(value, str):
                result[key] = text(value)
            elif key == "examples":
                result[key] = examples(value)
            elif key == "scopes" and isinstance(value, Mapping):
                result[key] = {scope: text(description) for scope, description in value.items()}
            elif key in _NAME_MAPS and isinstance(value, Mapping):
                result[key] = named(value)
            else:
                result[key] = walk(value)
        return result

    return walk(schema)  # type: ignore[no-any-return]


def _translate(value: str, translator: Translator, builtin_domain: str) -> str:
    """Try the openapi context, then the plain message, then the library's own catalog."""
    # Schema text is looked up as written; braces in a description are not placeholders.
    return (
        translator._find(value, context=OPENAPI_CONTEXT)
        or translator._find(value)
        or translator._find(value, context=OPENAPI_CONTEXT, domain=builtin_domain)
        or value
    )
