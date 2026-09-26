from __future__ import annotations

from typing import Annotated

import pytest
from fastapi import FastAPI, Header, Path, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from fastapi_locale import localize_errors


class Item(BaseModel):
    title: str = Field(min_length=3)
    price: int = Field(gt=0)
    tags: list[str] = Field(default_factory=list, max_length=2)


def routes(app: FastAPI) -> None:
    @app.post("/items/{item_id}")
    async def create(
        item_id: Annotated[int, Path(ge=1)],
        item: Item,
        page: Annotated[int, Query(le=10)] = 1,
        x_token: Annotated[str, Header(min_length=4)] = "abcd",
    ) -> Item:
        return item


BAD = {"title": "ab", "price": 0, "tags": ["a", "b", "c"]}


@pytest.fixture
def plain() -> TestClient:
    app = FastAPI()
    routes(app)
    return TestClient(app)


@pytest.fixture
def localized(app: FastAPI) -> TestClient:
    routes(app)
    return TestClient(app)


def call(client: TestClient, language: str) -> dict[str, list[dict[str, object]]]:
    response = client.post(
        "/items/0?page=11",
        json=BAD,
        headers={"Accept-Language": language, "X-Token": "ab"},
    )
    assert response.status_code == 422
    return response.json()  # type: ignore[no-any-return]


def test_english_is_identical_to_fastapi(plain: TestClient, localized: TestClient) -> None:
    assert call(localized, "en") == call(plain, "en")


def test_only_msg_differs(plain: TestClient, localized: TestClient) -> None:
    expected = call(plain, "en")["detail"]
    actual = call(localized, "de")["detail"]
    assert len(actual) == len(expected) == 6
    for before, after in zip(expected, actual, strict=True):
        assert {k: v for k, v in before.items() if k != "msg"} == {
            k: v for k, v in after.items() if k != "msg"
        }
    by_type = {error["type"]: error["msg"] for error in actual}
    assert by_type["greater_than"] == "Wert muss groesser als 0 sein (App)"


def test_missing_body_and_bad_json(localized: TestClient) -> None:
    missing = localized.post("/items/1", headers={"Accept-Language": "de"})
    assert missing.json()["detail"][0]["type"] == "missing"
    invalid = localized.post(
        "/items/1",
        content=b"{bad json",
        headers={"Content-Type": "application/json", "Accept-Language": "de"},
    )
    assert invalid.json()["detail"][0]["type"] == "json_invalid"


def test_applications_can_compose_their_own_handler(app: FastAPI) -> None:
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse

    async def handler(request: object, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse({"errors": [e["msg"] for e in localize_errors(exc)]}, status_code=400)

    app.add_exception_handler(RequestValidationError, handler)  # type: ignore[arg-type]
    routes(app)
    response = TestClient(app).post("/items/1", json=BAD, headers={"Accept-Language": "de"})
    assert response.status_code == 400
    assert "Wert muss groesser als 0 sein (App)" in response.json()["errors"]


@pytest.mark.parametrize(
    ("language", "greater_than", "too_short"),
    [
        (
            "fr",
            "L'entrée doit être supérieure à 0",
            "La chaîne doit contenir au moins 3 caractères",
        ),
        ("hi", "इनपुट 0 से बड़ा होना चाहिए", "string में कम से कम 3 अक्षर होने चाहिए"),
        ("pt-BR", "A entrada deve ser maior que 0", "A string deve ter pelo menos 3 caracteres"),
    ],
)
def test_builtin_translations(
    localized: TestClient, language: str, greater_than: str, too_short: str
) -> None:
    detail = localized.post("/items/1", json=BAD, headers={"Accept-Language": language}).json()[
        "detail"
    ]
    by_type = {error["type"]: error["msg"] for error in detail}
    assert by_type["greater_than"] == greater_than
    assert by_type["string_too_short"] == too_short
