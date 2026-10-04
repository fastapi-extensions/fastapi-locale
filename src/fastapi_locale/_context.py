"""Locale context: which translator is active for the current request or block (ADR-0003)."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import TYPE_CHECKING, Protocol

from fastapi_locale.exceptions import LocalizationNotConfiguredError, NoActiveRequestError

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fastapi_locale._locale import Locale
    from fastapi_locale._translator import Translator

__all__ = [
    "RequestLocale",
    "TranslatorProvider",
    "current_request_locale",
    "dgettext",
    "dngettext",
    "dnpgettext",
    "dpgettext",
    "enter_request",
    "exit_request",
    "get_locale",
    "get_process_default",
    "get_translator",
    "gettext",
    "gettext_noop",
    "ngettext",
    "npgettext",
    "pgettext",
    "set_locale",
    "set_process_default",
    "use_default_locale",
    "use_locale",
]


class TranslatorProvider(Protocol):
    """Anything that can hand out translators; implemented by the catalog store."""

    @property
    def default_translator(self) -> Translator: ...

    def translator_for(self, locale: str | Locale) -> Translator: ...


class RequestLocale:
    """The locale of one request and what chose it; available as ``request.state.locale``.

    ``set_locale()`` changes it during the request, so read it when the value is needed, for
    example when the access log line is written.
    """

    # One object per request, shared by every context copy made while the request is handled.
    __slots__ = ("_decided_by", "_provider", "_request", "_temporary", "_translator")

    def __init__(
        self,
        translator: Translator,
        decided_by: str,
        provider: TranslatorProvider,
        request: RequestLocale | None = None,
        *,
        temporary: bool = False,
    ) -> None:
        self._translator = translator
        self._decided_by = decided_by
        self._provider = provider
        # Set for use_locale() blocks: points at the request holder they shadow.
        self._request = request
        self._temporary = temporary

    @property
    def locale(self) -> Locale:
        """The locale the request is answered in."""
        return self._translator.locale

    @property
    def decided_by(self) -> str:
        """Name of the source that chose it, or ``default``, ``override`` or ``set_locale``."""
        return self._decided_by

    def __repr__(self) -> str:
        return f"RequestLocale({self.locale.tag!r}, decided_by={self._decided_by!r})"


_current: ContextVar[RequestLocale | None] = ContextVar(
    "fastapi_locale.request_locale", default=None
)
_process_default: TranslatorProvider | None = None


def set_process_default(provider: TranslatorProvider | None) -> None:
    """Set the provider used outside requests and ``use_locale`` blocks."""
    global _process_default  # noqa: PLW0603 - one process-wide fallback by design
    _process_default = provider


def get_process_default() -> TranslatorProvider | None:
    """Return the provider used outside requests, if one is set."""
    return _process_default


def enter_request(
    translator: Translator, decided_by: str, provider: TranslatorProvider
) -> tuple[RequestLocale, Token[RequestLocale | None]]:
    """Open the locale scope of a request; pair every call with ``exit_request``."""
    holder = RequestLocale(translator, decided_by, provider)
    return holder, _current.set(holder)


def exit_request(token: Token[RequestLocale | None]) -> None:
    """Close the locale scope opened by ``enter_request``."""
    _current.reset(token)


def current_request_locale() -> RequestLocale | None:
    """Return the holder of the current request or block, if any."""
    return _current.get()


def get_translator() -> Translator:
    """Return the active translator: block, then request, then process default."""
    holder = _current.get()
    if holder is not None:
        return holder._translator
    if _process_default is not None:
        return _process_default.default_translator
    msg = (
        "no localization is set up; create a Localization and call install(app) "
        "or make_default() before translating"
    )
    raise LocalizationNotConfiguredError(msg)


def get_locale() -> Locale:
    """Return the active locale."""
    return get_translator().locale


def set_locale(locale: str | Locale) -> Locale:
    """Change the locale for the rest of the current request and return the matched locale.

    Raises ``UnsupportedLocaleError`` when no supported locale matches, which includes ``None``
    and empty values, and ``NoActiveRequestError`` when called outside a request.
    """
    request = _request_holder(_current.get())
    if request is None:
        msg = "set_locale() works only during a request; use use_locale() for a block of code"
        raise NoActiveRequestError(msg)
    translator = request._provider.translator_for(locale)
    request._translator = translator
    request._decided_by = "set_locale"
    return translator.locale


@contextmanager
def use_locale(locale: str | Locale) -> Iterator[Locale]:
    """Make a locale active for a block of code and yield the matched locale.

    The request's own locale and its ``Content-Language`` header do not change. Raises
    ``UnsupportedLocaleError`` when no supported locale matches.
    """
    holder = _current.get()
    provider = holder._provider if holder is not None else _process_default
    if provider is None:
        msg = "no localization is set up; create a Localization before calling use_locale()"
        raise LocalizationNotConfiguredError(msg)
    translator = provider.translator_for(locale)
    with _block(translator, "use_locale", provider, holder):
        yield translator.locale


@contextmanager
def use_default_locale() -> Iterator[None]:
    """Make the default locale active for a block; does nothing where no localization is set up."""
    holder = _current.get()
    provider = holder._provider if holder is not None else _process_default
    if provider is None:
        yield
        return
    with _block(provider.default_translator, "default", provider, holder):
        yield


@contextmanager
def _block(
    translator: Translator,
    decided_by: str,
    provider: TranslatorProvider,
    holder: RequestLocale | None,
) -> Iterator[None]:
    token = _current.set(
        RequestLocale(translator, decided_by, provider, _request_holder(holder), temporary=True)
    )
    try:
        yield
    finally:
        _current.reset(token)


def _request_holder(holder: RequestLocale | None) -> RequestLocale | None:
    """Return the holder of the enclosing request, skipping use_locale() blocks."""
    if holder is None:
        return None
    return holder._request if holder._temporary else holder


def gettext(message: str, /, **params: object) -> str:
    """Translate a message in the active locale."""
    return get_translator().gettext(message, **params)


def ngettext(singular: str, plural: str, n: int, /, **params: object) -> str:
    """Translate a plural message in the active locale."""
    return get_translator().ngettext(singular, plural, n, **params)


def pgettext(context: str, message: str, /, **params: object) -> str:
    """Translate a message within a context in the active locale."""
    return get_translator().pgettext(context, message, **params)


def npgettext(context: str, singular: str, plural: str, n: int, /, **params: object) -> str:
    """Translate a plural message within a context in the active locale."""
    return get_translator().npgettext(context, singular, plural, n, **params)


def dgettext(domain: str, message: str, /, **params: object) -> str:
    """Translate a message from another domain in the active locale."""
    return get_translator().dgettext(domain, message, **params)


def dngettext(domain: str, singular: str, plural: str, n: int, /, **params: object) -> str:
    """Translate a plural message from another domain in the active locale."""
    return get_translator().dngettext(domain, singular, plural, n, **params)


def dpgettext(domain: str, context: str, message: str, /, **params: object) -> str:
    """Translate a message within a context, from another domain, in the active locale."""
    return get_translator().dpgettext(domain, context, message, **params)


def dnpgettext(
    domain: str, context: str, singular: str, plural: str, n: int, /, **params: object
) -> str:
    """Translate a plural message within a context, from another domain, in the active locale."""
    return get_translator().dnpgettext(domain, context, singular, plural, n, **params)


def gettext_noop(message: str, /) -> str:
    """Mark a message for extraction without translating it."""
    return message
