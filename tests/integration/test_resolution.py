from __future__ import annotations

from collections.abc import Callable, Sequence

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.requests import HTTPConnection

from fastapi_locale import (
    AcceptLanguageSource,
    CookieSource,
    LocaleConfig,
    LocaleDep,
    Localization,
    QueryParamSource,
)


def build(config: LocaleConfig) -> TestClient:
    app = FastAPI()
    Localization(config).install(app)

    @app.get("/")
    async def index(locale: LocaleDep, request: Request) -> dict[str, str]:
        return {"locale": locale.tag, "decided_by": request.state.locale.decided_by}

    return TestClient(app)


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({}, ("en", "default")),
        ({"headers": {"Accept-Language": "de"}}, ("de", "accept-language")),
        ({"headers": {"Accept-Language": "hi-IN,hi;q=0.9"}}, ("hi", "accept-language")),
        ({"headers": {"Accept-Language": "sw, fr;q=0.2"}}, ("fr", "accept-language")),
        ({"headers": {"Accept-Language": "sw"}}, ("en", "default")),
        ({"headers": {"Accept-Language": "de;q=0, fr"}}, ("fr", "accept-language")),
        ({"headers": {"Accept-Language": "pt-br"}}, ("pt-BR", "accept-language")),
        ({"params": {"lang": "ru"}, "headers": {"Accept-Language": "de"}}, ("ru", "query")),
        (
            {"params": {"lang": "../etc"}, "headers": {"Accept-Language": "de"}},
            ("de", "accept-language"),
        ),
        ({"cookies": {"locale": "ja"}, "headers": {"Accept-Language": "de"}}, ("ja", "cookie")),
        ({"params": {"lang": "fr"}, "cookies": {"locale": "ja"}}, ("fr", "query")),
    ],
)
def test_default_source_order(
    make_config: Callable[..., LocaleConfig], kwargs: dict[str, object], expected: tuple[str, str]
) -> None:
    client = build(make_config())
    if cookies := kwargs.pop("cookies", None):
        client.cookies.update(cookies)  # type: ignore[arg-type]
    body = client.get("/", **kwargs).json()  # type: ignore[arg-type]
    assert (body["locale"], body["decided_by"]) == expected


def test_configured_sources_and_order(make_config: Callable[..., LocaleConfig]) -> None:
    client = build(
        make_config(sources=[AcceptLanguageSource(), QueryParamSource("hl"), CookieSource("lng")])
    )
    assert client.get("/?hl=fr", headers={"Accept-Language": "de"}).json()["locale"] == "de"
    assert client.get("/?hl=fr").json()["locale"] == "fr"
    client.cookies["lng"] = "ja"
    assert client.get("/").json()["locale"] == "ja"


def test_custom_callable_sources(make_config: Callable[..., LocaleConfig]) -> None:
    def from_subdomain(conn: HTTPConnection) -> str | None:
        return conn.url.hostname.split(".")[0] if conn.url.hostname else None

    def several(conn: HTTPConnection) -> Sequence[str]:
        return ["sw", "ru"]

    def broken(conn: HTTPConnection) -> str:
        raise RuntimeError

    client = build(make_config(sources=[broken, from_subdomain, several]))
    body = client.get("http://de.example.com/").json()
    assert body == {"locale": "de", "decided_by": "from_subdomain"}
    assert client.get("http://www.example.com/").json() == {"locale": "ru", "decided_by": "several"}


def test_empty_source_list_always_uses_default(make_config: Callable[..., LocaleConfig]) -> None:
    client = build(make_config(sources=[]))
    assert client.get("/?lang=de", headers={"Accept-Language": "de"}).json()["locale"] == "en"
