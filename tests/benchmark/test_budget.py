"""Performance budgets from the SRS (NFR-01, NFR-02). Run with ``make bench``."""

from __future__ import annotations

from typing import Any

from starlette.requests import HTTPConnection

from fastapi_locale import Localization

RESOLUTION_BUDGET = 50e-6  # seconds, median (NFR-01)
LOOKUP_BUDGET = 5e-6


def connection() -> HTTPConnection:
    return HTTPConnection(
        {
            "type": "http",
            "path": "/",
            "query_string": b"",
            "headers": [
                (b"accept-language", b"sw-KE, hi-IN;q=0.9, en;q=0.8"),
                (b"cookie", b"session=abc"),
            ],
        }
    )


def test_resolution_budget(benchmark: Any, localization: Localization) -> None:
    result = benchmark(lambda: localization.resolve(connection()))
    assert result.locale.tag == "hi"
    assert benchmark.stats.stats.median < RESOLUTION_BUDGET


def test_lookup_budget(benchmark: Any, localization: Localization) -> None:
    translator = localization.translator("pt-BR")
    result = benchmark(translator.gettext, "Hello {name}", name="Ana")
    assert result == "Olá Ana"
    assert benchmark.stats.stats.median < LOOKUP_BUDGET
