from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from fastapi_locale import gettext_lazy

NOT_FOUND = gettext_lazy("Item not found")


def test_lazy_detail_forms(app: FastAPI, client: TestClient) -> None:
    @app.get("/plain")
    async def plain() -> None:
        raise HTTPException(status_code=404, detail=NOT_FOUND)

    @app.get("/nested")
    async def nested() -> None:
        raise HTTPException(status_code=409, detail={"reason": NOT_FOUND, "codes": [NOT_FOUND]})

    @app.get("/headers")
    async def headers() -> None:
        raise HTTPException(
            status_code=401, detail=NOT_FOUND, headers={"WWW-Authenticate": "Bearer"}
        )

    @app.get("/empty")
    async def empty() -> None:
        raise HTTPException(status_code=304)

    hindi = {"Accept-Language": "hi"}
    assert client.get("/plain", headers=hindi).json() == {"detail": "आइटम नहीं मिला"}
    assert client.get("/nested", headers=hindi).json() == {
        "detail": {"reason": "आइटम नहीं मिला", "codes": ["आइटम नहीं मिला"]}
    }
    response = client.get("/headers", headers={"Accept-Language": "de"})
    assert response.json() == {"detail": "Artikel nicht gefunden"}
    assert response.headers["www-authenticate"] == "Bearer"
    not_modified = client.get("/empty")
    assert not_modified.status_code == 304
    assert not_modified.content == b""


def test_starlette_errors_keep_default_text(client: TestClient) -> None:
    assert client.get("/nothing-here").json() == {"detail": "Not Found"}
