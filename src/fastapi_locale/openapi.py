"""Serve the OpenAPI schema in the request's locale (ADR-0009)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi_locale._catalog import BUILTIN_DOMAIN
from fastapi_locale._context import get_translator, use_default_locale
from fastapi_locale._openapi import translate_schema

if TYPE_CHECKING:
    from fastapi import FastAPI

__all__ = ["localize_openapi"]

_MARK = "__fastapi_locale__"


def localize_openapi(app: FastAPI) -> None:
    """Make ``app.openapi()`` return the schema translated into the active locale.

    ``Localization.install()`` calls it unless ``localize_openapi=False``. FastAPI still builds
    the schema once; each locale's translation is made on first use and kept until FastAPI
    builds a new schema. Customize ``app.openapi`` before calling this, not after.
    """
    build = app.openapi
    if getattr(build, _MARK, False):
        return
    base: dict[str, Any] | None = None
    translated: dict[str, dict[str, Any]] = {}

    def openapi() -> dict[str, Any]:
        nonlocal base
        translator = get_translator()
        # Text rendered while FastAPI builds the schema, such as a lazy default value, must not
        # depend on who asks first: the one shared schema is always built in the default locale.
        with use_default_locale():
            current = build()
        if current is not base:
            base = current
            translated.clear()
        schema = translated.get(translator.locale.tag)
        if schema is None:
            schema = translate_schema(current, translator, BUILTIN_DOMAIN)
            translated[translator.locale.tag] = schema
        return schema

    setattr(openapi, _MARK, True)
    app.openapi = openapi  # type: ignore[method-assign]
