from __future__ import annotations

from contextlib import suppress
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI, Header
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from fastapi_locale import LocaleDep, UnsupportedLocaleError, set_locale


class Body(BaseModel):
    price: int = Field(gt=0)


async def async_user(x_user_language: Annotated[str | None, Header()] = None) -> None:
    if x_user_language:
        set_locale(x_user_language)


def sync_user(x_user_language: Annotated[str | None, Header()] = None) -> None:
    if x_user_language:
        with suppress(UnsupportedLocaleError):
            set_locale(x_user_language)


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    for path, dependency in (("/async", async_user), ("/sync", sync_user)):

        @app.post(path, dependencies=[Depends(dependency)])
        def create(body: Body, locale: LocaleDep) -> dict[str, str]:
            return {"locale": locale.tag}

    return TestClient(app)


@pytest.mark.parametrize("path", ["/async", "/sync"])
def test_user_language_reaches_route_and_header(client: TestClient, path: str) -> None:
    response = client.post(
        path, json={"price": 1}, headers={"Accept-Language": "fr", "X-User-Language": "de"}
    )
    assert response.json() == {"locale": "de"}
    assert response.headers["content-language"] == "de"


@pytest.mark.parametrize("path", ["/async", "/sync"])
def test_user_language_reaches_validation_errors(client: TestClient, path: str) -> None:
    response = client.post(
        path, json={"price": 0}, headers={"Accept-Language": "fr", "X-User-Language": "de"}
    )
    assert response.status_code == 422
    assert response.headers["content-language"] == "de"
    assert response.json()["detail"][0]["msg"] == "Wert muss groesser als 0 sein (App)"


def test_unsupported_user_language_keeps_request_locale(client: TestClient) -> None:
    response = client.post(
        "/sync", json={"price": 1}, headers={"Accept-Language": "fr", "X-User-Language": "sw"}
    )
    assert response.json() == {"locale": "fr"}
