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
_DATA_KEYS = frozenset({"default", "example", "examples", "const", "enum"})


def translate_schema(
    schema: Mapping[str, Any], translator: Translator, builtin_domain: str
) -> dict[str, Any]:
    """Return a copy of ``schema`` with titles, summaries and descriptions translated."""
    cache: dict[str, str] = {}

    def text(value: str) -> str:
        if value not in cache:
            cache[value] = _translate(value, translator, builtin_domain)
        return cache[value]

    def walk(node: Any) -> Any:  # noqa: ANN401 - JSON values of any type
        if isinstance(node, Mapping):
            result: dict[str, Any] = {}
            for key, value in node.items():
                if key in _DATA_KEYS:
                    result[key] = value
                elif key in _TEXT_KEYS and isinstance(value, str):
                    result[key] = text(value)
                else:
                    result[key] = walk(value)
            return result
        if isinstance(node, list):
            return [walk(item) for item in node]
        return node

    return walk(schema)  # type: ignore[no-any-return]


def _translate(value: str, translator: Translator, builtin_domain: str) -> str:
    """Try the openapi context, then the plain message, then the library's own catalog."""
    for translated in (
        translator.pgettext(OPENAPI_CONTEXT, value),
        translator.gettext(value),
        translator.dpgettext(builtin_domain, OPENAPI_CONTEXT, value),
    ):
        if translated != value:
            return translated
    return value
