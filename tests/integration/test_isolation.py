from __future__ import annotations

import asyncio
import random

import httpx
import pytest
from fastapi import FastAPI

from fastapi_locale import gettext

EXPECTED = {"en": "Hello", "de": "Hallo", "fr": "Bonjour", "ru": "Привет", "ja": "こんにちは"}


@pytest.mark.anyio
async def test_concurrent_requests_never_mix_locales(app: FastAPI) -> None:
    @app.get("/async")
    async def async_route() -> dict[str, str]:
        await asyncio.sleep(random.random() / 100)  # noqa: S311 - jitter only
        return {"text": gettext("Hello")}

    @app.get("/sync")
    def sync_route() -> dict[str, str]:
        return {"text": gettext("Hello")}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        languages = [random.choice(list(EXPECTED)) for _ in range(300)]  # noqa: S311
        responses = await asyncio.gather(
            *(
                client.get(f"/{'async' if i % 2 else 'sync'}", headers={"Accept-Language": lang})
                for i, lang in enumerate(languages)
            )
        )
    for lang, response in zip(languages, responses, strict=True):
        assert response.json() == {"text": EXPECTED[lang]}
        assert response.headers["content-language"] == lang
