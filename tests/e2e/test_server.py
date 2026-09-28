from __future__ import annotations

import asyncio
import random

import httpx
import pytest

WELCOME = {
    "en": "Welcome to the inventory",
    "de": "Willkommen im Lager",
    "hi": "इन्वेंटरी में आपका स्वागत है",
}


def test_translated_responses_and_headers(server: str) -> None:
    response = httpx.get(server, headers={"Accept-Language": "de-CH, en;q=0.5"})
    assert response.json() == {"message": "Willkommen im Lager", "locale": "de"}
    assert response.headers["content-language"] == "de"
    assert response.headers["vary"] == "Cookie, Accept-Language"
    assert httpx.get(f"{server}/?lang=hi").json()["locale"] == "hi"


def test_lazy_text_in_models_and_errors(server: str) -> None:
    item = httpx.get(f"{server}/items/1", headers={"Accept-Language": "hi"}).json()
    assert item["status"] == "स्टॉक में है"
    missing = httpx.get(f"{server}/items/99", headers={"Accept-Language": "de"})
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Artikel nicht gefunden"}


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("en", "Input should be greater than 0"),
        ("de", "Eingabe muss größer als 0 sein"),
        ("hi", "इनपुट 0 से बड़ा होना चाहिए"),
    ],
)
def test_validation_errors(server: str, language: str, expected: str) -> None:
    response = httpx.post(
        f"{server}/items", json={"name": "ab", "quantity": 0}, headers={"Accept-Language": language}
    )
    assert response.status_code == 422
    messages = {error["type"]: error["msg"] for error in response.json()["detail"]}
    assert messages["greater_than"] == expected


def test_users_saved_language(server: str) -> None:
    created = httpx.post(
        f"{server}/items",
        json={"name": "Milk", "quantity": 3},
        headers={"Accept-Language": "de", "X-User-Language": "hi"},
    )
    assert created.status_code == 201
    assert created.headers["content-language"] == "hi"
    assert created.json()["summary"] == "Milk की 3 इकाइयाँ जोड़ी गईं"


@pytest.mark.anyio
async def test_parallel_requests_keep_their_own_language(server: str) -> None:
    languages = [random.choice(list(WELCOME)) for _ in range(200)]  # noqa: S311 - test data
    async with httpx.AsyncClient(base_url=server, timeout=10.0) as client:
        responses = await asyncio.gather(
            *(client.get("/", headers={"Accept-Language": lang}) for lang in languages)
        )
    for lang, response in zip(languages, responses, strict=True):
        assert response.json()["message"] == WELCOME[lang]


def test_api_documentation_follows_the_locale(server: str) -> None:
    schema = httpx.get(f"{server}/openapi.json", headers={"Accept-Language": "de"}).json()
    assert schema["info"]["title"] == "Lager"
    operation = schema["paths"]["/items/{item_id}"]["get"]
    assert operation["summary"] == "Einen Artikel lesen"
    assert operation["responses"]["422"]["description"] == "Validierungsfehler"
    english = httpx.get(f"{server}/openapi.json").json()
    assert english["info"]["title"] == "Inventory"
