from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from fastapi_locale import LazyText, gettext_lazy, ngettext_lazy


class Order(BaseModel):
    id: int
    status: LazyText = gettext_lazy("Pending")


def test_response_models_and_dicts(app: FastAPI, client: TestClient) -> None:
    @app.get("/model")
    async def model() -> Order:
        return Order(id=1)

    @app.get("/response-model", response_model=Order)
    async def response_model() -> dict[str, object]:
        return {"id": 2, "status": gettext_lazy("Pending")}

    @app.get("/dict")
    async def plain() -> dict[str, object]:
        return {"files": ngettext_lazy("{n} file", "{n} files", 3)}

    german = {"Accept-Language": "de"}
    assert client.get("/model", headers=german).json() == {"id": 1, "status": "Ausstehend"}
    assert client.get("/response-model", headers=german).json() == {"id": 2, "status": "Ausstehend"}
    assert client.get("/dict", headers=german).json() == {"files": "3 Dateien"}
    assert client.get("/dict", headers={"Accept-Language": "ru"}).json() == {"files": "3 файла"}


def test_openapi_still_builds(app: FastAPI, client: TestClient) -> None:
    @app.get("/model")
    async def model() -> Order:
        return Order(id=1)

    schema = client.get("/openapi.json").json()
    assert schema["components"]["schemas"]["Order"]["properties"]["status"]["type"] == "string"
