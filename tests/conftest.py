"""Shared fixtures: compiled test catalogs, a localization, and isolation of process state."""

from __future__ import annotations

import shutil
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastapi_locale import LocaleConfig, Localization
from fastapi_locale._context import get_process_default, set_process_default

pytest_plugins = ["pytester", "fastapi_locale.testing"]

DATA = Path(__file__).parent / "data"
LEVELS = ("unit", "integration", "e2e", "benchmark")

SUPPORTED = ["en", "de", "fr", "hi", "ru", "ar", "ja", "pt", "pt-BR"]


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark each test with its level, taken from its directory."""
    for item in items:
        for level in LEVELS:
            if f"/tests/{level}/" in item.path.as_posix():
                item.add_marker(getattr(pytest.mark, level))


def compile_catalogs(source: Path, target: Path) -> Path:
    """Copy a tree of .po files to ``target`` and compile each one next to its source."""
    if source != target:
        shutil.copytree(source, target, dirs_exist_ok=True)
    for po in target.rglob("*.po"):
        with po.open("rb") as stream:
            catalog = read_po(stream, locale=po.parent.parent.name)
        with po.with_suffix(".mo").open("wb") as stream:
            write_mo(stream, catalog)
    return target


@pytest.fixture(scope="session")
def catalog_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Compiled test catalogs, shared by the whole session."""
    return compile_catalogs(DATA / "locales", tmp_path_factory.mktemp("catalogs") / "locales")


@pytest.fixture
def anyio_backend() -> str:
    """Run async tests on asyncio."""
    return "asyncio"


@pytest.fixture(autouse=True)
def _isolate_process_default() -> Iterator[None]:
    previous = get_process_default()
    set_process_default(None)
    yield
    set_process_default(previous)


@pytest.fixture
def make_config(catalog_dir: Path) -> Callable[..., LocaleConfig]:
    """Build a config over the test catalogs, with overridable fields."""

    def make(**overrides: object) -> LocaleConfig:
        values: dict[str, object] = {
            "default_locale": "en",
            "supported_locales": SUPPORTED,
            "catalog_dirs": [catalog_dir],
        }
        values.update(overrides)
        return LocaleConfig(**values)  # type: ignore[arg-type]

    return make


@pytest.fixture
def localization(make_config: Callable[..., LocaleConfig]) -> Localization:
    """A localization over the test catalogs."""
    return Localization(make_config())


@pytest.fixture
def app(localization: Localization) -> FastAPI:
    """An empty application with the localization installed."""
    application = FastAPI()
    localization.install(application)
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """Test client for ``app``."""
    with TestClient(app) as test_client:
        yield test_client
