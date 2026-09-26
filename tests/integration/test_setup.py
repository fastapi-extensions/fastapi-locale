from __future__ import annotations

import logging
from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from fastapi_locale import (
    ConfigurationError,
    LocaleConfig,
    LocaleMiddleware,
    Localization,
    LocalizationNotConfiguredError,
    get_locale,
    gettext,
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


def test_first_install_becomes_process_default(
    localization: Localization, make_config: Callable[..., LocaleConfig]
) -> None:
    with pytest.raises(LocalizationNotConfiguredError):
        gettext("Hello")
    localization.install(FastAPI())
    other = Localization(make_config(default_locale="de"))
    other.install(FastAPI())
    assert get_process_default() is localization.store
    other.make_default()
    assert get_locale().tag == "de"


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


def test_properties(localization: Localization) -> None:
    assert localization.default_locale.tag == "en"
    assert localization.supported_locales[1].tag == "de"
    assert localization.vary == ("Cookie", "Accept-Language")
    assert localization.config.default_domain == "messages"
