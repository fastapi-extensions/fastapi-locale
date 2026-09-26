from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastapi_locale import (
    LocaleDep,
    Localization,
    TranslatorDep,
    current_locale,
    current_translator,
)


def test_dependencies_and_overrides(
    app: FastAPI, client: TestClient, localization: Localization
) -> None:
    @app.get("/")
    async def index(locale: LocaleDep, tr: TranslatorDep) -> dict[str, str]:
        return {"locale": locale.tag, "text": tr.gettext("Hello")}

    assert client.get("/?lang=de").json() == {"locale": "de", "text": "Hallo"}

    app.dependency_overrides[current_locale] = lambda: localization.translator("ja").locale
    app.dependency_overrides[current_translator] = lambda: localization.translator("fr")
    assert client.get("/?lang=de").json() == {"locale": "ja", "text": "Bonjour"}
