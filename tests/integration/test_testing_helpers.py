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


def test_locale_marker_arguments(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import pytest
        from fastapi_locale import LocaleConfig, Localization, get_locale

        config = LocaleConfig(default_locale="en", supported_locales=["en", "fr"])
        Localization(config).make_default()

        @pytest.mark.locale(tag="fr")
        def test_keyword():
            assert get_locale().tag == "fr"

        @pytest.mark.locale
        def test_without_a_tag():
            pass
        """
    )
    result = pytester.runpytest("-p", "fastapi_locale.testing")
    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(["*the locale marker needs a language tag*"])


def test_default_localization_is_put_back_after_each_test(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        from fastapi import FastAPI
        from fastapi_locale import LocaleConfig, Localization, get_locale

        Localization(LocaleConfig(default_locale="en", supported_locales=["en"])).make_default()

        def test_installs_another_localization():
            config = LocaleConfig(default_locale="fr", supported_locales=["fr"])
            Localization(config).install(FastAPI())
            assert get_locale().tag == "fr"

        def test_sees_the_original_default():
            assert get_locale().tag == "en"
        """
    )
    pytester.runpytest("-p", "fastapi_locale.testing").assert_outcomes(passed=2)
