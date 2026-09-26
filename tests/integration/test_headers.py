from __future__ import annotations

from collections.abc import Callable, Iterator

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

from fastapi_locale import LocaleConfig, Localization, QueryParamSource


def test_content_language_and_vary(app: FastAPI, client: TestClient) -> None:
    @app.get("/")
    async def index() -> dict[str, str]:
        return {}

    response = client.get("/", headers={"Accept-Language": "de"})
    assert response.headers["content-language"] == "de"
    assert response.headers["vary"] == "Cookie, Accept-Language"


def test_existing_headers_are_respected(app: FastAPI, client: TestClient) -> None:
    @app.get("/own")
    async def own(response: Response) -> dict[str, str]:
        response.headers["Content-Language"] = "x-custom"
        response.headers["Vary"] = "Origin, accept-language"
        return {}

    @app.get("/star")
    async def star(response: Response) -> dict[str, str]:
        response.headers["Vary"] = "*"
        return {}

    response = client.get("/own", headers={"Accept-Language": "de"})
    assert response.headers["content-language"] == "x-custom"
    assert response.headers["vary"] == "Origin, accept-language, Cookie"
    assert client.get("/star").headers["vary"] == "*"


def test_streaming_and_error_responses(app: FastAPI, client: TestClient) -> None:
    @app.get("/stream")
    async def stream() -> StreamingResponse:
        def chunks() -> Iterator[bytes]:
            yield b"a"
            yield b"b"

        return StreamingResponse(chunks())

    @app.get("/missing")
    async def missing() -> None:
        raise HTTPException(status_code=404)

    for path in ("/stream", "/missing", "/no-such-route"):
        response = client.get(path, headers={"Accept-Language": "fr"})
        assert response.headers["content-language"] == "fr", path


def test_no_vary_when_sources_read_no_headers(make_config: Callable[..., LocaleConfig]) -> None:
    app = FastAPI()
    Localization(make_config(sources=[QueryParamSource()])).install(app)

    @app.get("/")
    async def index() -> dict[str, str]:
        return {}

    response = TestClient(app).get("/?lang=de")
    assert response.headers["content-language"] == "de"
    assert "vary" not in response.headers
