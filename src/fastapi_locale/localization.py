"""Localization: loads catalogs and wires the library into a FastAPI application."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import exception_handlers as fastapi_handlers
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from fastapi_locale._catalog import CatalogStore
from fastapi_locale._context import get_process_default, set_process_default
from fastapi_locale._locale import Locale
from fastapi_locale.exceptions import ConfigurationError
from fastapi_locale.handlers import http_exception_handler, validation_exception_handler
from fastapi_locale.middleware import LocaleMiddleware
from fastapi_locale.sources import default_sources, source_name, source_vary

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fastapi import FastAPI
    from starlette.requests import HTTPConnection

    from fastapi_locale._translator import Translator
    from fastapi_locale.config import LocaleConfig
    from fastapi_locale.sources import LocaleSourceLike

__all__ = ["Localization", "Resolution"]

logger = logging.getLogger("fastapi_locale")


@dataclass(frozen=True, slots=True)
class Resolution:
    """The locale chosen for a request and the source that decided it."""

    locale: Locale
    decided_by: str


class Localization:
    """Catalogs, locale resolution and FastAPI integration for one configuration."""

    def __init__(self, config: LocaleConfig) -> None:
        self._config = config
        self._default = Locale.parse(config.default_locale)
        self._store = CatalogStore.load(
            supported=config.locales,
            default=self._default,
            source=Locale.parse(config.source_locale),
            directories=config.catalog_dirs,  # type: ignore[arg-type]  # normalized to Path
            builtin=config.builtin_error_messages,
            default_domain=config.default_domain,
        )
        self._sources: tuple[LocaleSourceLike, ...] = (
            tuple(config.sources) if config.sources is not None else default_sources()
        )
        vary: list[str] = []
        for source in self._sources:
            vary.extend(h for h in source_vary(source) if h.lower() not in map(str.lower, vary))
        self._vary = tuple(vary)
        self._forced: Locale | None = None

    @property
    def config(self) -> LocaleConfig:
        """The configuration this localization was built from."""
        return self._config

    @property
    def store(self) -> CatalogStore:
        """The loaded catalogs."""
        return self._store

    @property
    def default_locale(self) -> Locale:
        """Locale used when no source matches."""
        return self._default

    @property
    def supported_locales(self) -> tuple[Locale, ...]:
        """Locales this application serves, in configured order."""
        return self._config.locales

    @property
    def vary(self) -> tuple[str, ...]:
        """Request headers read by the configured sources."""
        return self._vary

    def install(self, app: FastAPI) -> None:
        """Add the middleware and exception handlers to ``app``; safe to call twice."""
        existing = getattr(app.state, "localization", None)
        if existing is self:
            return
        if existing is not None:
            msg = "this application already has a different Localization installed"
            raise ConfigurationError(msg)
        app.state.localization = self
        app.add_middleware(LocaleMiddleware, localization=self)
        _set_handler(
            app,
            RequestValidationError,
            fastapi_handlers.request_validation_exception_handler,
            validation_exception_handler,
        )
        _set_handler(
            app, HTTPException, fastapi_handlers.http_exception_handler, http_exception_handler
        )
        if get_process_default() is None:
            self.make_default()

    def make_default(self) -> None:
        """Use this localization for code that runs outside requests."""
        set_process_default(self._store)

    def translator(self, locale: str | Locale) -> Translator:
        """Return the translator for a supported locale."""
        return self._store.translator_for(locale)

    def resolve(self, conn: HTTPConnection) -> Resolution:
        """Pick the locale for a request from the configured sources."""
        if self._forced is not None:
            return Resolution(self._forced, "override")
        for source in self._sources:
            try:
                candidates = source(conn)
            except Exception:  # A custom source must never break a request.
                logger.warning("Locale source %s failed", source_name(source), exc_info=True)
                continue
            if not candidates:
                continue
            for candidate in (candidates,) if isinstance(candidates, str) else candidates:
                locale = self._store.match(candidate)
                if locale is not None:
                    logger.debug("Locale %s chosen by %s", locale.tag, source_name(source))
                    return Resolution(locale, source_name(source))
        return Resolution(self._default, "default")

    @contextmanager
    def override(self, locale: str | Locale) -> Iterator[Locale]:
        """Force every request in the block to one locale; meant for tests."""
        forced = self._store.translator_for(locale).locale
        previous, self._forced = self._forced, forced
        try:
            yield forced
        finally:
            self._forced = previous


def _set_handler(app: FastAPI, exc_class: type[Exception], default: object, ours: object) -> None:
    current = app.exception_handlers.get(exc_class)
    if current is None or current is default:
        app.add_exception_handler(exc_class, ours)  # type: ignore[arg-type]
    else:
        logger.info("Keeping the application's own handler for %s", exc_class.__name__)
