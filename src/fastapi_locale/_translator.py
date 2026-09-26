"""Translator bound to one locale, reading its precomputed fallback chains."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fastapi_locale._formatting import format_message

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from fastapi_locale._locale import Locale

__all__ = ["Catalog", "MessageKey", "Translator", "english_plural"]

logger = logging.getLogger("fastapi_locale")

MessageKey = str | tuple[str, int]

# gettext joins a message context and its msgid with this separator.
_CONTEXT_SEPARATOR = "\x04"
# Bound on remembered warnings, so dynamic msgids cannot grow memory without limit.
_MAX_WARNINGS = 1024


def english_plural(n: int) -> int:
    """Plural rule gettext uses when a catalog declares none."""
    return int(n != 1)


@dataclass(frozen=True, slots=True)
class Catalog:
    """Messages of one domain for one locale, keyed the way gettext stores them."""

    locale: str
    domain: str
    messages: Mapping[MessageKey, str]
    plural: Callable[[int], int] = english_plural
    sources: tuple[str, ...] = field(default=())


class Translator:
    """Translate messages for exactly one locale, in any loaded domain."""

    __slots__ = ("_chains", "_default_domain", "_locale", "_warned")

    def __init__(
        self,
        locale: Locale,
        chains: Mapping[str, tuple[Catalog, ...]],
        default_domain: str,
    ) -> None:
        self._locale = locale
        self._chains = dict(chains)
        self._default_domain = default_domain
        self._warned: set[tuple[str, str, str]] = set()

    @property
    def locale(self) -> Locale:
        """The locale this translator serves."""
        return self._locale

    @property
    def default_domain(self) -> str:
        """Domain used by the functions without a ``d`` prefix."""
        return self._default_domain

    def gettext(self, message: str, /, **params: object) -> str:
        """Translate a message."""
        return self.translate(message, params=params)

    def ngettext(self, singular: str, plural: str, n: int, /, **params: object) -> str:
        """Translate a message with a plural form chosen by ``n``."""
        return self.translate(singular, plural=plural, n=n, params=params)

    def pgettext(self, context: str, message: str, /, **params: object) -> str:
        """Translate a message within a context."""
        return self.translate(message, context=context, params=params)

    def npgettext(
        self, context: str, singular: str, plural: str, n: int, /, **params: object
    ) -> str:
        """Translate a message within a context, with a plural form chosen by ``n``."""
        return self.translate(singular, plural=plural, n=n, context=context, params=params)

    def dgettext(self, domain: str, message: str, /, **params: object) -> str:
        """Translate a message from another domain."""
        return self.translate(message, domain=domain, params=params)

    def dngettext(
        self, domain: str, singular: str, plural: str, n: int, /, **params: object
    ) -> str:
        """Translate a plural message from another domain."""
        return self.translate(singular, plural=plural, n=n, domain=domain, params=params)

    def dpgettext(self, domain: str, context: str, message: str, /, **params: object) -> str:
        """Translate a message within a context, from another domain."""
        return self.translate(message, context=context, domain=domain, params=params)

    def dnpgettext(
        self,
        domain: str,
        context: str,
        singular: str,
        plural: str,
        n: int,
        /,
        **params: object,
    ) -> str:
        """Translate a plural message within a context, from another domain."""
        return self.translate(
            singular, plural=plural, n=n, context=context, domain=domain, params=params
        )

    def translate(
        self,
        message: str,
        *,
        plural: str | None = None,
        n: int | None = None,
        context: str | None = None,
        domain: str | None = None,
        params: Mapping[str, object] | None = None,
    ) -> str:
        """Look up a message along the fallback chain and fill its placeholders."""
        domain = domain or self._default_domain
        text = self._lookup(domain, context, message, plural, n)
        values: Mapping[str, object] = params or {}
        if plural is not None and n is not None and "n" not in values:
            values = {"n": n, **values}
        if not values:
            return text
        return format_message(text, values, lambda name: self._warn_missing(domain, message, name))

    def _lookup(
        self,
        domain: str,
        context: str | None,
        singular: str,
        plural: str | None,
        n: int | None,
    ) -> str:
        key = singular if context is None else f"{context}{_CONTEXT_SEPARATOR}{singular}"
        for catalog in self._chains.get(domain, ()):
            if plural is not None and n is not None:
                found = catalog.messages.get((key, catalog.plural(n)))
            else:
                found = catalog.messages.get(key)
            if found:  # an empty translation counts as missing
                return found
        if plural is not None and n is not None and n != 1:
            return plural
        return singular

    def _warn_missing(self, domain: str, message: str, name: str) -> None:
        key = (domain, message, name)
        if key in self._warned or len(self._warned) >= _MAX_WARNINGS:
            return
        self._warned.add(key)
        logger.warning(
            "Translation has no value for placeholder {%s} (locale=%s, domain=%s, msgid=%r)",
            name,
            self._locale.tag,
            domain,
            message,
        )

    def __repr__(self) -> str:
        return f"Translator({self._locale.tag!r})"
