"""FastAPI dependencies that expose the active locale and translator."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from fastapi_locale._context import get_translator
from fastapi_locale._locale import Locale
from fastapi_locale._translator import Translator

__all__ = ["LocaleDep", "TranslatorDep", "current_locale", "current_translator"]


# Async on purpose: FastAPI runs sync dependencies in a thread pool, which would cost a thread
# hop on every request for a simple context variable read.
async def current_locale() -> Locale:
    """Provide the active locale; replace it with ``app.dependency_overrides`` in tests."""
    return get_translator().locale


async def current_translator() -> Translator:
    """Provide the active translator; replace it with ``app.dependency_overrides`` in tests."""
    return get_translator()


LocaleDep = Annotated[Locale, Depends(current_locale)]
TranslatorDep = Annotated[Translator, Depends(current_translator)]
