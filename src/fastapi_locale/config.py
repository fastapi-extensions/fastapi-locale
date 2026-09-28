"""Application-facing configuration."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi_locale._locale import Locale
from fastapi_locale.exceptions import ConfigurationError

if TYPE_CHECKING:
    import os
    from collections.abc import Sequence

    from fastapi_locale.sources import LocaleSourceLike

__all__ = ["LocaleConfig"]

_DOMAIN = re.compile(r"[A-Za-z0-9_.-]+")


@dataclass(frozen=True, slots=True, kw_only=True)
class LocaleConfig:
    """Settings for a ``Localization``; values are validated and normalized on creation."""

    default_locale: str
    supported_locales: Sequence[str]
    catalog_dirs: Sequence[str | os.PathLike[str]] = ()
    default_domain: str = "messages"
    source_locale: str = "en"
    sources: Sequence[LocaleSourceLike] | None = None
    builtin_error_messages: bool = True
    localize_openapi: bool = True

    def __post_init__(self) -> None:
        if isinstance(self.supported_locales, str):
            msg = "supported_locales must be a list of tags, not a single string"
            raise ConfigurationError(msg)
        supported = tuple(_parse("supported_locales", value) for value in self.supported_locales)
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
        directories = tuple(Path(directory) for directory in self.catalog_dirs)
        for directory in directories:
            if not directory.is_dir():
                msg = f"catalog_dirs entry is not a directory: {directory}"
                raise ConfigurationError(msg)
        if not _DOMAIN.fullmatch(self.default_domain):
            msg = f"default_domain {self.default_domain!r} may only use letters, digits, _ - ."
            raise ConfigurationError(msg)

        object.__setattr__(self, "supported_locales", tuple(tags))
        object.__setattr__(self, "default_locale", default.tag)
        object.__setattr__(self, "source_locale", source.tag)
        object.__setattr__(self, "catalog_dirs", directories)
        if self.sources is not None:
            object.__setattr__(self, "sources", tuple(self.sources))

    @property
    def locales(self) -> tuple[Locale, ...]:
        """Supported locales as parsed values."""
        return tuple(Locale.parse(tag) for tag in self.supported_locales)


def _parse(field: str, value: object) -> Locale:
    locale = Locale.try_parse(value) if isinstance(value, str) else None
    if locale is None:
        msg = f"{field}: {value!r} is not a valid language tag"
        raise ConfigurationError(msg)
    return locale
