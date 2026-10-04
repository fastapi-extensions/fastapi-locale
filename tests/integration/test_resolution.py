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
    gettext,
    set_locale,
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
        ({"headers": {"Accept-Language": "pt-PT, de;q=0.5"}}, ("pt", "accept-language")),
    ],
)
def test_default_source_order(
    make_config: Callable[..., LocaleConfig], kwargs: dict[str, object], expected: tuple[str, str]
) -> None:
    client = build(make_config())
    client.cookies["locale"] = "ja"  # no cookie source by default, so this is not read
    body = client.get("/", **kwargs).json()  # type: ignore[arg-type]
    assert (body["locale"], body["decided_by"]) == expected


def test_cookie_source(make_config: Callable[..., LocaleConfig]) -> None:
    sources = [QueryParamSource(), CookieSource(), AcceptLanguageSource()]
    client = build(make_config(sources=sources))
    client.cookies["locale"] = "ja"
    german = {"Accept-Language": "de"}
    assert client.get("/", headers=german).json() == {"locale": "ja", "decided_by": "cookie"}
    assert client.get("/?lang=fr").json() == {"locale": "fr", "decided_by": "query"}
    client.cookies["locale"] = "not a tag"
    assert client.get("/", headers=german).json()["decided_by"] == "accept-language"


def test_another_region_of_the_language_is_better_than_the_default(
    make_config: Callable[..., LocaleConfig],
) -> None:
    client = build(make_config(supported_locales=["en", "pt-BR", "de"]))
    for header in ("pt", "pt-PT, pt;q=0.9, de;q=0.8"):
        assert client.get("/", headers={"Accept-Language": header}).json()["locale"] == "pt-BR"


def test_source_language_request_with_another_default_locale(
    make_config: Callable[..., LocaleConfig],
) -> None:
    app = FastAPI()
    Localization(make_config(default_locale="de")).install(app)

    @app.get("/")
    async def index(n: int = 0) -> dict[str, str]:
        return {"text": gettext("Hello")}

    client = TestClient(app)
    english = {"Accept-Language": "en"}
    assert client.get("/", headers=english).json() == {"text": "Hello"}
    assert (
        client.get("/?n=x", headers=english).json()["detail"][0]["msg"].startswith("Input should")
    )
    assert client.get("/").json() == {"text": "Hallo"}


def test_configured_sources_and_order(make_config: Callable[..., LocaleConfig]) -> None:
    sources = [AcceptLanguageSource(), QueryParamSource(param="hl"), CookieSource(cookie="lng")]
    client = build(make_config(sources=sources))
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


def test_sources_that_return_unusable_values_are_skipped(
    make_config: Callable[..., LocaleConfig], caplog: pytest.LogCaptureFixture
) -> None:
    def header_or_nothing(conn: HTTPConnection) -> list[str | None]:
        return [conn.headers.get("x-lang")]

    def wrong_types(conn: HTTPConnection) -> object:
        return [5, b"de", {"de": 1}]

    def not_iterable(conn: HTTPConnection) -> object:
        return 5

    sources = [header_or_nothing, wrong_types, not_iterable, QueryParamSource()]
    client = build(make_config(sources=sources))
    assert client.get("/?lang=fr").json() == {"locale": "fr", "decided_by": "query"}
    assert client.get("/", headers={"X-Lang": "ru"}).json()["decided_by"] == "header_or_nothing"
    assert "Locale source not_iterable failed" in caplog.text


def test_set_locale_is_recorded_as_the_deciding_source(app: FastAPI, client: TestClient) -> None:
    @app.get("/")
    async def index(request: Request) -> dict[str, str]:
        before = request.state.locale.decided_by
        set_locale("de")
        return {"before": before, "after": request.state.locale.decided_by}

    assert client.get("/?lang=fr").json() == {"before": "query", "after": "set_locale"}
