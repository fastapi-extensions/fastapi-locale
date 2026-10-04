"""Application-facing configuration."""

from __future__ import annotations

import os
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi_locale._locale import Locale
from fastapi_locale.exceptions import ConfigurationError

if TYPE_CHECKING:
    from fastapi_locale.sources import LocaleSource

__all__ = ["LocaleConfig"]

_DOMAIN = re.compile(r"[A-Za-z0-9_.-]+")


@dataclass(frozen=True, slots=True, kw_only=True)
class LocaleConfig:
    """Settings for a ``Localization``; values are validated and normalized on creation.

    Invalid values raise ``ConfigurationError`` naming the option.

    Attributes:
        default_locale: Locale used when no source matches; one of ``supported_locales``.
        supported_locales: Every locale the application serves, as language tags.
        catalog_dirs: Directories laid out as ``<dir>/<locale>/LC_MESSAGES/<domain>.mo``; later
            directories override earlier ones.
        default_domain: Domain used by ``gettext()`` and the other functions without a ``d``.
        source_locale: Language the msgids are written in; it needs no catalog.
        sources: Where a request's locale comes from, in order; ``None`` means the ``lang``
            query parameter, then ``Accept-Language``.
        builtin_catalogs: Load the library's own translations of validation errors and of
            FastAPI's schema text.
        localize_openapi: Serve the OpenAPI schema in the request's locale.
    """

    default_locale: str
    supported_locales: Sequence[str]
    catalog_dirs: Sequence[str | os.PathLike[str]] = ()
    default_domain: str = "messages"
    source_locale: str = "en"
    sources: Sequence[LocaleSource] | None = None
    builtin_catalogs: bool = True
    localize_openapi: bool = True

    def __post_init__(self) -> None:
        supported = [
            _parse("supported_locales", value)
            for value in _items("supported_locales", self.supported_locales)
        ]
        if not supported:
            msg = "supported_locales must name at least one locale"
            raise ConfigurationError(msg)
        tags = [locale.tag for locale in supported]
        duplicates = sorted({tag for tag in tags if tags.count(tag) > 1})
        if duplicates:
            msg = f"supported_locales has duplicates after normalization: {duplicates}"
            raise ConfigurationError(msg)
        default = _parse("default_locale", self.default_locale)
        if default.tag not in tags:
            msg = f"default_locale {default.tag!r} must be one of supported_locales {tags}"
            raise ConfigurationError(msg)
        source = _parse("source_locale", self.source_locale)
        directories = tuple(
            _directory(value) for value in _items("catalog_dirs", self.catalog_dirs)
        )
        if not _DOMAIN.fullmatch(self.default_domain):
            msg = f"default_domain {self.default_domain!r} may only use letters, digits, _ - ."
            raise ConfigurationError(msg)

        object.__setattr__(self, "supported_locales", tuple(tags))
        object.__setattr__(self, "default_locale", default.tag)
        object.__setattr__(self, "source_locale", source.tag)
        object.__setattr__(self, "catalog_dirs", directories)
        if self.sources is not None:
            sources = tuple(_items("sources", self.sources))
            for candidate in sources:
                # A class instead of an instance is callable too, but would be called per request.
                if not callable(candidate) or isinstance(candidate, type):
                    msg = (
                        f"sources: {candidate!r} is not a locale source; pass a function "
                        "or an instance such as QueryParamSource()"
                    )
                    raise ConfigurationError(msg)
            object.__setattr__(self, "sources", sources)


def _items(option: str, value: object) -> Iterable[Any]:
    """Return the items of a list option; a single string or path is a mistake, not a list."""
    if isinstance(value, (str, bytes, os.PathLike)) or not isinstance(value, Iterable):
        msg = f"{option} must be a list, not a single {type(value).__name__}"
        raise ConfigurationError(msg)
    return value


def _parse(option: str, value: object) -> Locale:
    locale = Locale.try_parse(value)
    if locale is None:
        msg = f"{option}: {value!r} is not a valid language tag"
        raise ConfigurationError(msg)
    return locale


def _directory(value: object) -> Path:
    if not isinstance(value, (str, os.PathLike)):
        msg = f"catalog_dirs: {value!r} is not a path"
        raise ConfigurationError(msg)
    return Path(value)
