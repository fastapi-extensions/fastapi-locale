"""Serve the OpenAPI schema in the request's locale (ADR-0009)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi_locale._catalog import BUILTIN_DOMAIN
from fastapi_locale._context import get_translator
from fastapi_locale._openapi import translate_schema

if TYPE_CHECKING:
    from fastapi import FastAPI

__all__ = ["localize_openapi"]


def localize_openapi(app: FastAPI) -> None:
    """Make ``app.openapi()`` return the schema translated into the active locale.

    FastAPI still builds the schema once; each locale's translation is made on first use and cached.
    Swagger UI and ReDoc fetch the schema with the browser's ``Accept-Language``, so they follow it.
    """
    build = app.openapi
    translated: dict[str, dict[str, Any]] = {}

    def openapi() -> dict[str, Any]:
        translator = get_translator()
        schema = translated.get(translator.locale.tag)
        if schema is None:
            schema = translate_schema(build(), translator, BUILTIN_DOMAIN)
            translated[translator.locale.tag] = schema
        return schema

    app.openapi = openapi  # type: ignore[method-assign]
