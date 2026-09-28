from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from fastapi_locale import LocaleConfig, Localization, gettext_noop, use_locale


class Item(BaseModel):
    title: str = Field(description=gettext_noop("Hello"))


def build(config: LocaleConfig) -> FastAPI:
    app = FastAPI(title=gettext_noop("Orders API"))
    Localization(config).install(app)

    @app.post("/items", summary=gettext_noop("Item"))
    async def create(item: Item) -> Item:
        return item

    return app


def test_schema_follows_the_request_locale(make_config: Callable[..., LocaleConfig]) -> None:
    client = TestClient(build(make_config()))
    english = client.get("/openapi.json").json()
    response = client.get("/openapi.json", headers={"Accept-Language": "de"})
    german = response.json()

    assert english["info"]["title"] == "Orders API"
    assert german["info"]["title"] == "Bestell-API"
    operation = german["paths"]["/items"]["post"]
    assert operation["summary"] == "Artikel (Schema)"
    assert operation["responses"]["422"]["description"] == "Validierungsfehler"
    item = german["components"]["schemas"]["Item"]
    assert item["properties"]["title"]["description"] == "Hallo"
    error_fields = german["components"]["schemas"]["ValidationError"]["properties"]
    assert error_fields["msg"]["title"] == "Meldung"
    assert response.headers["content-language"] == "de"
    assert "Accept-Language" in response.headers["vary"]


def test_each_locale_is_built_once(make_config: Callable[..., LocaleConfig]) -> None:
    app = build(make_config())
    app.state.localization.make_default()
    with use_locale("de"):
        assert app.openapi() is app.openapi()
    assert app.openapi()["info"]["title"] == "Orders API"


def test_can_be_turned_off(make_config: Callable[..., LocaleConfig]) -> None:
    client = TestClient(build(make_config(localize_openapi=False)))
    german = client.get("/openapi.json", headers={"Accept-Language": "de"}).json()
    assert german["info"]["title"] == "Orders API"


def test_docs_page_still_works(make_config: Callable[..., LocaleConfig]) -> None:
    client = TestClient(build(make_config()))
    assert client.get("/docs", headers={"Accept-Language": "de"}).status_code == 200
