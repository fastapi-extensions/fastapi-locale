"""Pure ASGI middleware that resolves the locale of each request (ADR-0004)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.datastructures import MutableHeaders
from starlette.requests import HTTPConnection

from fastapi_locale._context import enter_request, exit_request

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

    from fastapi_locale.localization import Localization

__all__ = ["LocaleMiddleware"]


class LocaleMiddleware:
    """Resolve the locale before routing and add ``Content-Language`` and ``Vary`` to responses."""

    def __init__(self, app: ASGIApp, localization: Localization) -> None:
        self.app = app
        self.localization = localization

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle one ASGI connection."""
        if scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return

        resolution = self.localization.resolve(HTTPConnection(scope))
        store = self.localization.store
        holder, token = enter_request(
            store.translator_for(resolution.locale), resolution.decided_by, store
        )
        scope.setdefault("state", {})["locale"] = holder
        vary = self.localization.vary

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                message.setdefault("headers", [])
                headers = MutableHeaders(scope=message)
                if "content-language" not in headers:
                    headers["content-language"] = holder.locale.tag
                if vary:
                    _merge_vary(headers, vary)
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        finally:
            exit_request(token)


def _merge_vary(headers: MutableHeaders, additions: tuple[str, ...]) -> None:
    current = [value.strip() for value in headers.get("vary", "").split(",") if value.strip()]
    if "*" in current:
        return
    seen = {value.lower() for value in current}
    for header in additions:
        if header.lower() not in seen:
            current.append(header)
            seen.add(header.lower())
    headers["vary"] = ", ".join(current)
