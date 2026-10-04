"""Pure ASGI middleware that resolves the locale of each request (ADR-0004)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.datastructures import MutableHeaders
from starlette.requests import HTTPConnection

from fastapi_locale._context import current_request_locale, enter_request, exit_request

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

    from fastapi_locale.localization import Localization

__all__ = ["LocaleMiddleware"]


class LocaleMiddleware:
    """Resolve the locale before routing and add ``Content-Language`` and ``Vary`` to responses.

    ``Localization.install()`` adds it; add it yourself only when you wire the library by hand.

    Args:
        app: The ASGI application to wrap.
        localization: The localization that resolves the locale.
    """

    def __init__(self, app: ASGIApp, localization: Localization) -> None:
        self.app = app
        self.localization = localization

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle one ASGI connection."""
        if scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return

        store = self.localization._store
        state = scope.setdefault("state", {})
        outer = current_request_locale()
        if outer is not None and outer._provider is store and state.get("locale") is outer:
            # The same localization already opened this request further out, as it does for a
            # mounted application that has it installed too. One holder serves the whole request.
            await self.app(scope, receive, send)
            return

        locale, decided_by = self.localization._resolve(HTTPConnection(scope))
        holder, token = enter_request(store.translator_for(locale), decided_by, store)
        state["locale"] = holder
        vary = self.localization._vary

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
    # A response may carry several Vary lines; all of them are folded into one.
    current = [
        value.strip()
        for line in headers.getlist("vary")
        for value in line.split(",")
        if value.strip()
    ]
    if "*" in current:
        return
    seen = {value.lower() for value in current}
    for header in additions:
        if header.lower() not in seen:
            current.append(header)
            seen.add(header.lower())
    headers["vary"] = ", ".join(current)
