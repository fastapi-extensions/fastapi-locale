"""Pytest helpers. Enable with ``pytest_plugins = ["fastapi_locale.testing"]``."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from fastapi_locale._context import use_locale

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = ["locale_marker"]


def pytest_configure(config: pytest.Config) -> None:
    """Register the ``locale`` marker."""
    config.addinivalue_line("markers", "locale(tag): run the test body with this locale active")


@pytest.fixture(autouse=True)
def locale_marker(request: pytest.FixtureRequest) -> Iterator[None]:
    """Apply ``@pytest.mark.locale("hi")`` by running the test inside ``use_locale("hi")``."""
    marker = request.node.get_closest_marker("locale")
    if marker is None:
        yield
        return
    with use_locale(marker.args[0]):
        yield
