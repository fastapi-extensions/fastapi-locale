from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from fastapi_locale import ConfigurationError, LocaleConfig, QueryParamSource


def test_values_are_normalized(catalog_dir: Path) -> None:
    config = LocaleConfig(
        default_locale="pt_br",
        supported_locales=["EN", "pt_BR"],
        catalog_dirs=[str(catalog_dir)],
        source_locale="EN",
    )
    assert config.default_locale == "pt-BR"
    assert config.supported_locales == ("en", "pt-BR")
    assert config.source_locale == "en"
    assert config.catalog_dirs == (catalog_dir,)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"supported_locales": "en"}, "supported_locales must be a list"),
        ({"supported_locales": None}, "supported_locales must be a list"),
        ({"supported_locales": []}, "at least one"),
        ({"supported_locales": ["en", "EN"]}, "duplicates"),
        ({"supported_locales": ["en", "x"]}, "'x' is not a valid"),
        ({"supported_locales": ["en", None]}, "None is not a valid"),
        ({"default_locale": "de-AT"}, "must be one of"),
        ({"source_locale": "??"}, "source_locale"),
        ({"catalog_dirs": "locales"}, "catalog_dirs must be a list"),
        ({"catalog_dirs": Path("locales")}, "catalog_dirs must be a list"),
        ({"catalog_dirs": [5]}, "5 is not a path"),
        ({"default_domain": "../x"}, "default_domain"),
        ({"sources": QueryParamSource()}, "sources must be a list"),
        ({"sources": [QueryParamSource]}, "not a locale source"),
        ({"sources": ["lang"]}, "not a locale source"),
    ],
)
def test_invalid_values_are_rejected(
    make_config: Callable[..., LocaleConfig], overrides: dict[str, object], message: str
) -> None:
    with pytest.raises(ConfigurationError, match=message):
        make_config(**overrides)


def test_configuration_does_not_touch_the_filesystem(
    make_config: Callable[..., LocaleConfig],
) -> None:
    config = make_config(catalog_dirs=["/does/not/exist"])
    assert config.catalog_dirs == (Path("/does/not/exist"),)


def test_sources_are_frozen(make_config: Callable[..., LocaleConfig]) -> None:
    def source(conn: object) -> None:
        return None

    config = make_config(sources=[source])
    assert config.sources == (source,)
