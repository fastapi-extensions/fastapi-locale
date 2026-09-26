"""Locale sources: where a request's language preference can come from."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from fastapi_locale._accept_language import DEFAULT_MAX_LENGTH, parse_accept_language

if TYPE_CHECKING:
    from starlette.requests import HTTPConnection

__all__ = [
    "AcceptLanguageSource",
    "CookieSource",
    "LocaleSource",
    "LocaleSourceLike",
    "QueryParamSource",
    "default_sources",
    "source_name",
    "source_vary",
]


@runtime_checkable
class LocaleSource(Protocol):
    """Return candidate language tags for a request, most preferred first.

    A source must be fast, must not do I/O and must not raise. ``vary`` names the request headers it
    reads, so responses can be cached per language.
    """

    name: str
    vary: tuple[str, ...]

    def __call__(self, conn: HTTPConnection, /) -> Sequence[str]:
        """Return candidate tags for this request."""
        ...


LocaleSourceLike = LocaleSource | Callable[["HTTPConnection"], "str | Sequence[str] | None"]


class QueryParamSource:
    """Read the locale from a query parameter, ``?lang=hi`` by default."""

    vary: tuple[str, ...] = ()

    def __init__(self, param: str = "lang") -> None:
        self.param = param
        self.name = "query"

    def __call__(self, conn: HTTPConnection, /) -> Sequence[str]:
        """Return candidate tags for this request."""
        value = conn.query_params.get(self.param)
        return [value] if value else []


class CookieSource:
    """Read the locale from a cookie, ``locale`` by default."""

    vary: tuple[str, ...] = ("Cookie",)

    def __init__(self, name: str = "locale") -> None:
        self.cookie = name
        self.name = "cookie"

    def __call__(self, conn: HTTPConnection, /) -> Sequence[str]:
        """Return candidate tags for this request."""
        value = conn.cookies.get(self.cookie)
        return [value] if value else []


class AcceptLanguageSource:
    """Read the locale from the ``Accept-Language`` header, honouring q-values."""

    vary: tuple[str, ...] = ("Accept-Language",)

    def __init__(self, max_length: int = DEFAULT_MAX_LENGTH) -> None:
        self.max_length = max_length
        self.name = "accept-language"

    def __call__(self, conn: HTTPConnection, /) -> Sequence[str]:
        """Return candidate tags for this request."""
        header = ", ".join(conn.headers.getlist("accept-language"))
        return parse_accept_language(header, self.max_length) if header else []


def default_sources() -> tuple[LocaleSource, ...]:
    """Query parameter ``lang``, then cookie ``locale``, then ``Accept-Language``."""
    return (QueryParamSource(), CookieSource(), AcceptLanguageSource())


def source_name(source: LocaleSourceLike) -> str:
    """Name recorded as the deciding source."""
    name = getattr(source, "name", None) or getattr(source, "__name__", None)
    return str(name) if name else type(source).__name__


def source_vary(source: LocaleSourceLike) -> tuple[str, ...]:
    """Request headers a source reads."""
    return tuple(getattr(source, "vary", ()))
