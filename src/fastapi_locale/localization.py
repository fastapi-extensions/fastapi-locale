"""Localization: loads catalogs and wires the library into a FastAPI application."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import exception_handlers as fastapi_handlers
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from fastapi_locale._catalog import CatalogStore
from fastapi_locale._context import set_process_default
from fastapi_locale._locale import Locale
from fastapi_locale.exceptions import ConfigurationError
from fastapi_locale.handlers import http_exception_handler, validation_exception_handler
from fastapi_locale.middleware import LocaleMiddleware
from fastapi_locale.openapi import localize_openapi
from fastapi_locale.sources import default_sources, source_name, source_vary

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fastapi import FastAPI
    from starlette.requests import HTTPConnection

    from fastapi_locale._translator import Translator
    from fastapi_locale.config import LocaleConfig
    from fastapi_locale.sources import LocaleSource

__all__ = ["Localization"]

logger = logging.getLogger("fastapi_locale")


class Localization:
    """Catalogs, locale resolution and FastAPI integration for one configuration.

    Creating it loads every catalog, so a missing directory or a broken file raises
    ``CatalogLoadError`` before the application starts.

    Args:
        config: The settings to use.
    """

    def __init__(self, config: LocaleConfig) -> None:
        self._config = config
        self._default = Locale.parse(config.default_locale)
        self._store = CatalogStore.load(
            supported=[Locale.parse(tag) for tag in config.supported_locales],
            default=self._default,
            source=Locale.parse(config.source_locale),
            directories=[Path(directory) for directory in config.catalog_dirs],
            builtin=config.builtin_catalogs,
            default_domain=config.default_domain,
        )
        sources = config.sources if config.sources is not None else default_sources()
        self._sources: tuple[tuple[str, LocaleSource], ...] = tuple(
            (source_name(source), source) for source in sources
        )
        vary: list[str] = []
        for _, source in self._sources:
            vary.extend(h for h in source_vary(source) if h.lower() not in map(str.lower, vary))
        self._vary = tuple(vary)
        self._forced: Locale | None = None

    @property
    def config(self) -> LocaleConfig:
        """The configuration this localization was built from."""
        return self._config

    def install(self, app: FastAPI) -> None:
        """Add the middleware and exception handlers to ``app`` and make this the default.

        Call it before the application starts, once for each FastAPI application including
        mounted ones. Calling it again for the same application does nothing.
        """
        existing = getattr(app.state, "localization", None)
        if existing is self:
            return
        if existing is not None:
            msg = "this application already has a different Localization installed"
            raise ConfigurationError(msg)
        # Starlette refuses new middleware once the application has started; nothing else may
        # be registered before that is known to have worked.
        app.add_middleware(LocaleMiddleware, localization=self)
        app.state.localization = self
        _set_handler(
            app,
            RequestValidationError,
            fastapi_handlers.request_validation_exception_handler,
            validation_exception_handler,
        )
        _set_handler(
            app, HTTPException, fastapi_handlers.http_exception_handler, http_exception_handler
        )
        if self._config.localize_openapi:
            localize_openapi(app)
        self.make_default()

    def make_default(self) -> None:
        """Use this localization for code that runs outside requests."""
        set_process_default(self._store)

    def translator(self, locale: str | Locale) -> Translator:
        """Return the translator for a supported locale."""
        return self._store.translator_for(locale)

    @contextmanager
    def override(self, locale: str | Locale) -> Iterator[Locale]:
        """Force every request in the block to one locale and yield it; meant for tests."""
        forced = self._store.translator_for(locale).locale
        previous, self._forced = self._forced, forced
        try:
            yield forced
        finally:
            self._forced = previous

    def _resolve(self, conn: HTTPConnection) -> tuple[Locale, str]:
        """Pick the locale for a connection and name what decided it."""
        if self._forced is not None:
            return self._forced, "override"
        for name, source in self._sources:
            try:
                candidates = source(conn)
                if isinstance(candidates, str):
                    candidates = (candidates,)
                for candidate in candidates or ():
                    locale = self._store.match(candidate)
                    if locale is not None:
                        logger.debug("Locale %s chosen by %s", locale.tag, name)
                        return locale, name
            except Exception:  # A source must never break a request, whatever it returns.
                logger.warning("Locale source %s failed", name, exc_info=True)
        return self._default, "default"


def _set_handler(app: FastAPI, exc_class: type[Exception], default: object, ours: object) -> None:
    current = app.exception_handlers.get(exc_class)
    if current is None or current is default:
        app.add_exception_handler(exc_class, ours)  # type: ignore[arg-type]
    else:
        logger.info("Keeping the application's own handler for %s", exc_class.__name__)
