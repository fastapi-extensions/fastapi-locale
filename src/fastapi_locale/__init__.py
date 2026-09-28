"""Internationalization for FastAPI: gettext catalogs, per-request locales and localized errors."""

from fastapi_locale._context import (
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
    UnsupportedLocaleError,
)
from fastapi_locale.handlers import (
    http_exception_handler,
    localize_errors,
    validation_exception_handler,
)
from fastapi_locale.lazy import (
    LazyText,
    gettext_lazy,
    ngettext_lazy,
    npgettext_lazy,
    pgettext_lazy,
)
from fastapi_locale.localization import Localization, Resolution
from fastapi_locale.middleware import LocaleMiddleware
from fastapi_locale.openapi import localize_openapi
from fastapi_locale.sources import (
    AcceptLanguageSource,
    CookieSource,
    LocaleSource,
    QueryParamSource,
)

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
    "QueryParamSource",
    "Resolution",
    "Translator",
    "TranslatorDep",
    "UnsupportedLocaleError",
    "current_locale",
    "current_translator",
    "dgettext",
    "dngettext",
    "dnpgettext",
    "dpgettext",
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
