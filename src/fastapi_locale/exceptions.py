"""Exceptions raised by fastapi-locale."""

from __future__ import annotations

__all__ = [
    "CatalogLoadError",
    "ConfigurationError",
    "LocalizationError",
    "LocalizationNotConfiguredError",
    "NoActiveRequestError",
    "UnsupportedLocaleError",
]


class LocalizationError(Exception):
    """Base class for the errors this library raises on purpose."""


class ConfigurationError(LocalizationError, ValueError):
    """The configuration passed to the library is invalid."""


class CatalogLoadError(LocalizationError):
    """A catalog directory or file could not be read."""


class UnsupportedLocaleError(LocalizationError, LookupError):
    """A locale was requested that the application does not support."""


class LocalizationNotConfiguredError(LocalizationError, RuntimeError):
    """Translation was requested where no localization is available."""


class NoActiveRequestError(LocalizationError, RuntimeError):
    """The request's locale was changed where no request is being handled."""
