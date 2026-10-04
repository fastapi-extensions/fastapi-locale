from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from fastapi_locale import (
    CatalogLoadError,
    ConfigurationError,
    LocaleConfig,
    LocaleMiddleware,
    Localization,
    LocalizationNotConfiguredError,
    get_locale,
    gettext,
    gettext_lazy,
    set_locale,
    use_locale,
)
from fastapi_locale._context import get_process_default


def test_install_is_idempotent(localization: Localization) -> None:
    app = FastAPI()
    localization.install(app)
    localization.install(app)
    assert sum(getattr(m, "cls", None) is LocaleMiddleware for m in app.user_middleware) == 1


def test_a_second_localization_is_rejected(
    localization: Localization, make_config: Callable[..., LocaleConfig]
) -> None:
    app = FastAPI()
    localization.install(app)
    with pytest.raises(ConfigurationError, match="already has"):
        Localization(make_config()).install(app)


def test_latest_install_becomes_process_default(
    localization: Localization, make_config: Callable[..., LocaleConfig]
) -> None:
    with pytest.raises(LocalizationNotConfiguredError):
        gettext("Hello")
    localization.install(FastAPI())
    assert get_process_default() is localization._store
    other = Localization(make_config(default_locale="de"))
    other.install(FastAPI())
    assert get_locale().tag == "de"
    localization.make_default()
    assert get_locale().tag == "en"


def test_install_after_startup_changes_nothing(localization: Localization) -> None:
    app = FastAPI()
    TestClient(app).get("/")  # the first request builds the middleware stack
    with pytest.raises(RuntimeError, match="Cannot add middleware"):
        localization.install(app)
    assert not hasattr(app.state, "localization")
    assert get_process_default() is None


def test_missing_catalog_directory_fails_when_catalogs_load(
    make_config: Callable[..., LocaleConfig], tmp_path: Path
) -> None:
    config = make_config(catalog_dirs=[tmp_path / "missing"])
    with pytest.raises(CatalogLoadError, match="does not exist"):
        Localization(config)


def test_own_handlers_are_kept(
    localization: Localization, caplog: pytest.LogCaptureFixture
) -> None:
    async def mine(request: object, exc: Exception) -> JSONResponse:
        return JSONResponse({"mine": True}, status_code=400)

    app = FastAPI(exception_handlers={RequestValidationError: mine})
    with caplog.at_level(logging.INFO, logger="fastapi_locale"):
        localization.install(app)
    assert app.exception_handlers[RequestValidationError] is mine
    assert "Keeping the application's own handler" in caplog.text


def test_two_applications_in_one_process(make_config: Callable[..., LocaleConfig]) -> None:
    german_first = FastAPI()
    Localization(make_config(default_locale="de")).install(german_first)
    french_first = FastAPI()
    Localization(make_config(default_locale="fr")).install(french_first)
    for application in (german_first, french_first):

        @application.get("/")
        async def index() -> dict[str, str]:
            return {"text": gettext("Hello")}

    assert TestClient(german_first).get("/").json() == {"text": "Hallo"}
    assert TestClient(french_first).get("/").json() == {"text": "Bonjour"}


def test_lifespan_scopes_pass_through(app: FastAPI) -> None:
    with TestClient(app) as client:
        assert client.get("/docs").status_code == 200


def test_installed_localization_is_reachable(app: FastAPI, localization: Localization) -> None:
    assert app.state.localization is localization
    assert localization.config.default_domain == "messages"


def test_mounted_application_shares_the_request_locale(localization: Localization) -> None:
    app, mounted = FastAPI(), FastAPI()
    app.mount("/sub", mounted)
    localization.install(app)
    localization.install(mounted)

    @mounted.get("/items/{item_id}")
    async def read(item_id: int, request: Request) -> dict[str, str]:
        if item_id == 0:
            raise HTTPException(status_code=404, detail=gettext_lazy("Item not found"))
        set_locale("fr")
        return {"decided_by": request.state.locale.decided_by}

    client = TestClient(app)
    german = {"Accept-Language": "de"}
    assert client.get("/sub/items/0", headers=german).json() == {"detail": "Artikel nicht gefunden"}
    invalid = client.get("/sub/items/x", headers={"Accept-Language": "fr"})
    assert invalid.json()["detail"][0]["msg"].startswith("L'entrée doit être un entier")
    changed = client.get("/sub/items/1", headers=german)
    assert changed.json() == {"decided_by": "set_locale"}
    assert changed.headers["content-language"] == "fr"


def test_middleware_order_decides_what_sees_the_locale(localization: Localization) -> None:
    app = FastAPI()
    seen: dict[str, str] = {}

    @app.middleware("http")
    async def inner(request: Request, call_next: Any) -> Any:
        seen["inner"] = get_locale().tag
        return await call_next(request)

    localization.install(app)

    @app.middleware("http")
    async def outer(request: Request, call_next: Any) -> Any:
        seen["outer"] = get_locale().tag
        response = await call_next(request)
        seen["outer afterwards"] = request.state.locale.locale.tag
        return response

    @app.get("/")
    async def index() -> dict[str, str]:
        return {}

    TestClient(app).get("/", headers={"Accept-Language": "de"})
    assert seen == {"inner": "de", "outer": "en", "outer afterwards": "de"}


def test_handler_for_unhandled_errors_can_use_the_request_locale(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def on_error(request: Request, exc: Exception) -> JSONResponse:
        outside = gettext("Hello")
        with use_locale(request.state.locale.locale):
            inside = gettext("Hello")
        return JSONResponse({"outside": outside, "inside": inside}, status_code=500)

    @app.get("/")
    async def index() -> None:
        raise RuntimeError

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/", headers={"Accept-Language": "de"})
    assert response.json() == {"outside": "Hello", "inside": "Hallo"}
