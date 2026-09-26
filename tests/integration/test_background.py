from __future__ import annotations

from fastapi import BackgroundTasks, FastAPI
from fastapi.testclient import TestClient

from fastapi_locale import gettext


def test_background_tasks_see_the_request_locale(app: FastAPI, client: TestClient) -> None:
    seen: list[str] = []

    @app.post("/")
    async def index(tasks: BackgroundTasks) -> dict[str, str]:
        tasks.add_task(lambda: seen.append(gettext("Hello")))
        return {}

    client.post("/", headers={"Accept-Language": "ja"})
    assert seen == ["こんにちは"]
