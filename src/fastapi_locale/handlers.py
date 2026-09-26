"""Exception handlers that render error responses in the request locale."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi.encoders import jsonable_encoder
from fastapi.utils import is_body_allowed_for_status_code
from starlette.responses import JSONResponse, Response

from fastapi_locale._context import get_translator
from fastapi_locale._errors_catalog import ErrorLocalizer

if TYPE_CHECKING:
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException
    from starlette.requests import Request

__all__ = ["http_exception_handler", "localize_errors", "validation_exception_handler"]

_localizer = ErrorLocalizer()

# FastAPI's handler uses the literal 422 as well, rather than the renamed status constant.
_UNPROCESSABLE = 422


def localize_errors(exc: RequestValidationError) -> list[dict[str, object]]:
    """Return the validation errors of ``exc`` with ``msg`` in the active locale."""
    return _localizer.localize(exc.errors(), get_translator())


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> Response:
    """Same response as FastAPI's default handler, with each ``msg`` translated."""
    return JSONResponse(
        status_code=_UNPROCESSABLE,
        content={"detail": jsonable_encoder(localize_errors(exc))},
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> Response:
    """Same response as FastAPI's default handler, rendering lazy text in ``detail``."""
    headers = getattr(exc, "headers", None)
    if not is_body_allowed_for_status_code(exc.status_code):
        return Response(status_code=exc.status_code, headers=headers)
    return JSONResponse(
        {"detail": jsonable_encoder(exc.detail)},
        status_code=exc.status_code,
        headers=headers,
    )
