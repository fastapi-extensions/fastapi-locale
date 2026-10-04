"""Locale sources: where a request's language preference can come from."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from fastapi_locale._accept_language import DEFAULT_MAX_LENGTH, parse_accept_language

if TYPE_CHECKING:
    from collections.abc import Sequence

    from starlette.requests import HTTPConnection

__all__ = ["AcceptLanguageSource", "CookieSource", "LocaleSource", "QueryParamSource"]


class LocaleSource(Protocol):
    """A callable that returns the language tags a request asks for, most preferred first.

    Any function that takes the connection and returns a tag, a sequence of tags or ``None`` is a
    source. It must be fast and must not do I/O. Two optional attributes refine it: ``name`` is
    recorded as the deciding source and defaults to the function or class name, and ``vary`` is a
    tuple of the request headers it reads, which are added to the ``Vary`` response header.
    """

    def __call__(self, conn: HTTPConnection, /) -> str | Sequence[str] | None:
        """Return the tags this request asks for, or nothing."""
        ...


class QueryParamSource:
    """Read the locale from a query parameter.

    Args:
        param: Name of the query parameter.
    """

    name = "query"
    vary: tuple[str, ...] = ()

    def __init__(self, param: str = "lang") -> None:
        self.param = param

    def __call__(self, conn: HTTPConnection, /) -> Sequence[str]:
        """Return the tags this request asks for."""
        value = conn.query_params.get(self.param)
        return [value] if value else []


class CookieSource:
    """Read the locale from a cookie.

    Args:
        cookie: Name of the cookie.
    """

    name = "cookie"
    vary: tuple[str, ...] = ("Cookie",)

    def __init__(self, cookie: str = "locale") -> None:
        self.cookie = cookie

    def __call__(self, conn: HTTPConnection, /) -> Sequence[str]:
        """Return the tags this request asks for."""
        value = conn.cookies.get(self.cookie)
        return [value] if value else []


class AcceptLanguageSource:
    """Read the locale from the ``Accept-Language`` header, honouring q-values.

    Args:
        max_length: Header values longer than this, 1024 characters by default, are cut at the
            last complete member before parsing.
    """

    name = "accept-language"
    vary: tuple[str, ...] = ("Accept-Language",)

    def __init__(self, max_length: int = DEFAULT_MAX_LENGTH) -> None:
        self.max_length = max_length

    def __call__(self, conn: HTTPConnection, /) -> Sequence[str]:
        """Return the tags this request asks for."""
        header = ", ".join(conn.headers.getlist("accept-language"))
        return parse_accept_language(header, self.max_length) if header else []


def default_sources() -> tuple[LocaleSource, ...]:
    """Query parameter ``lang``, then ``Accept-Language``."""
    return (QueryParamSource(), AcceptLanguageSource())


def source_name(source: LocaleSource) -> str:
    """Name recorded as the deciding source."""
    name = getattr(source, "name", None) or getattr(source, "__name__", None)
    return str(name) if name else type(source).__name__


def source_vary(source: LocaleSource) -> tuple[str, ...]:
    """Request headers a source reads."""
    return tuple(getattr(source, "vary", ()))
