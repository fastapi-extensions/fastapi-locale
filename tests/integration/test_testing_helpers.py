from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastapi_locale import Localization, gettext


def test_override_forces_every_request(app: FastAPI, localization: Localization) -> None:
    @app.get("/")
    async def index() -> dict[str, str]:
        return {"text": gettext("Hello")}

    client = TestClient(app)
    with localization.override("hi-IN") as forced:
        assert forced.tag == "hi"
        assert client.get("/?lang=de").json() == {"text": "नमस्ते"}
    assert client.get("/?lang=de").json() == {"text": "Hallo"}


def test_locale_marker_needs_a_localization(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import pytest
        from fastapi_locale import LocaleConfig, Localization, gettext

        config = LocaleConfig(default_locale="en", supported_locales=["en", "fr"])
        Localization(config).make_default()

        @pytest.mark.locale("fr")
        def test_marker():
            from fastapi_locale import get_locale
            assert get_locale().tag == "fr"

        def test_without_marker():
            from fastapi_locale import get_locale
            assert get_locale().tag == "en"
        """
    )
    pytester.runpytest("-p", "fastapi_locale.testing").assert_outcomes(passed=2)
