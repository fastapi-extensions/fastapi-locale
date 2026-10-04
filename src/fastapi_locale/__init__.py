"""Internationalization for FastAPI: gettext catalogs, per-request locales and localized errors."""

from importlib.metadata import PackageNotFoundError, version

from fastapi_locale._context import (
    RequestLocale,
    dgettext,
    dngettext,
    dnpgettext,
    dpgettext,
    get_locale,
    get_translator,
    gettext,
    gettext_noop,
    ngettext,
    npgettext,
    pgettext,
    set_locale,
    use_locale,
)
from fastapi_locale._locale import Locale
from fastapi_locale._translator import Translator
from fastapi_locale.config import LocaleConfig
from fastapi_locale.dependencies import (
    LocaleDep,
    TranslatorDep,
    current_locale,
    current_translator,
)
from fastapi_locale.exceptions import (
    CatalogLoadError,
    ConfigurationError,
    LocalizationError,
    LocalizationNotConfiguredError,
    NoActiveRequestError,
    UnsupportedLocaleError,
)
from fastapi_locale.handlers import (
    http_exception_handler,
    localize_errors,
    validation_exception_handler,
)
from fastapi_locale.lazy import (
    LazyText,
    dgettext_lazy,
    dngettext_lazy,
    dnpgettext_lazy,
    dpgettext_lazy,
    gettext_lazy,
    ngettext_lazy,
    npgettext_lazy,
    pgettext_lazy,
)
from fastapi_locale.localization import Localization
from fastapi_locale.middleware import LocaleMiddleware
from fastapi_locale.openapi import localize_openapi
from fastapi_locale.sources import (
    AcceptLanguageSource,
    CookieSource,
    LocaleSource,
    QueryParamSource,
)

try:
    __version__ = version("fastapi-locale")
except PackageNotFoundError:  # pragma: no cover - only in a source tree that is not installed
    __version__ = "0+unknown"

__all__ = [
    "AcceptLanguageSource",
    "CatalogLoadError",
    "ConfigurationError",
    "CookieSource",
    "LazyText",
    "Locale",
    "LocaleConfig",
    "LocaleDep",
    "LocaleMiddleware",
    "LocaleSource",
    "Localization",
    "LocalizationError",
    "LocalizationNotConfiguredError",
    "NoActiveRequestError",
    "QueryParamSource",
    "RequestLocale",
    "Translator",
    "TranslatorDep",
    "UnsupportedLocaleError",
    "current_locale",
    "current_translator",
    "dgettext",
    "dgettext_lazy",
    "dngettext",
    "dngettext_lazy",
    "dnpgettext",
    "dnpgettext_lazy",
    "dpgettext",
    "dpgettext_lazy",
    "get_locale",
    "get_translator",
    "gettext",
    "gettext_lazy",
    "gettext_noop",
    "http_exception_handler",
    "localize_errors",
    "localize_openapi",
    "ngettext",
    "ngettext_lazy",
    "npgettext",
    "npgettext_lazy",
    "pgettext",
    "pgettext_lazy",
    "set_locale",
    "use_locale",
    "validation_exception_handler",
]
