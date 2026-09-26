"""Exceptions raised by fastapi-locale."""

from __future__ import annotations

__all__ = [
    "CatalogLoadError",
    "ConfigurationError",
    "LocalizationError",
    "LocalizationNotConfiguredError",
    "UnsupportedLocaleError",
]


class LocalizationError(Exception):
    """Base class for every error raised by this library."""


class ConfigurationError(LocalizationError, ValueError):
    """The configuration passed to the library is invalid."""


class CatalogLoadError(LocalizationError):
    """A catalog directory or file could not be read."""


class UnsupportedLocaleError(LocalizationError, LookupError):
    """A locale was requested that the application does not support."""


class LocalizationNotConfiguredError(LocalizationError, RuntimeError):
    """Translation was requested where no localization is available."""
