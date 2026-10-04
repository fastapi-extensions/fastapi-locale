"""Pytest helpers. Enable with ``pytest_plugins = ["fastapi_locale.testing"]``.

The plugin adds the ``locale`` marker: ``@pytest.mark.locale("hi")`` runs the test body with
that locale active, as ``use_locale("hi")`` would. It also puts back, after each test, the
localization that code outside requests used before the test.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from fastapi_locale._context import get_process_default, set_process_default, use_locale

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = ["locale_marker"]


def pytest_configure(config: pytest.Config) -> None:
    """Register the ``locale`` marker."""
    config.addinivalue_line("markers", "locale(tag): run the test body with this locale active")


@pytest.fixture(autouse=True)
def locale_marker(request: pytest.FixtureRequest) -> Iterator[None]:
    """Apply the ``locale`` marker and isolate the default localization between tests."""
    previous = get_process_default()
    try:
        marker = request.node.get_closest_marker("locale")
        if marker is None:
            yield
        else:
            with use_locale(_tag(marker)):
                yield
    finally:
        set_process_default(previous)


def _tag(marker: pytest.Mark) -> str:
    tag = marker.args[0] if marker.args else marker.kwargs.get("tag")
    if not isinstance(tag, str):
        msg = 'the locale marker needs a language tag, for example @pytest.mark.locale("hi")'
        raise pytest.UsageError(msg)
    return tag
