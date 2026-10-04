"""The public API is the set of names exported by ``fastapi_locale``; this file pins it."""

from __future__ import annotations

import importlib

import pytest

import fastapi_locale

PUBLIC = {
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
}

# Modules without a leading underscore export public names only.
PUBLIC_MODULES = [
    "config",
    "dependencies",
    "exceptions",
    "handlers",
    "lazy",
    "localization",
    "middleware",
    "openapi",
    "sources",
]


def test_exported_names_are_exactly_the_public_api() -> None:
    assert set(fastapi_locale.__all__) == PUBLIC
    assert len(fastapi_locale.__all__) == len(PUBLIC)
    assert fastapi_locale.__all__ == sorted(fastapi_locale.__all__)
    for name in PUBLIC:
        assert getattr(fastapi_locale, name) is not None


@pytest.mark.parametrize("name", PUBLIC_MODULES)
def test_public_modules_export_public_names_only(name: str) -> None:
    module = importlib.import_module(f"fastapi_locale.{name}")
    assert set(module.__all__) <= PUBLIC
    for exported in module.__all__:
        assert getattr(module, exported) is getattr(fastapi_locale, exported)


def test_version_is_the_installed_distribution_version() -> None:
    from importlib.metadata import version

    assert fastapi_locale.__version__ == version("fastapi-locale")
