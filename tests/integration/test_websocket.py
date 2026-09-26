from __future__ import annotations

from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient

from fastapi_locale import gettext


def test_websockets_get_a_locale(app: FastAPI, client: TestClient) -> None:
    @app.websocket("/ws")
    async def ws(websocket: WebSocket) -> None:
        await websocket.accept()
        await websocket.send_text(gettext("Hello"))
        await websocket.close()

    with client.websocket_connect("/ws?lang=fr") as connection:
        assert connection.receive_text() == "Bonjour"
