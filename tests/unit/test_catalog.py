from __future__ import annotations

import logging
from pathlib import Path

import pytest

from fastapi_locale import CatalogLoadError, Locale, UnsupportedLocaleError
from fastapi_locale._catalog import CatalogStore
from tests.conftest import SUPPORTED, compile_catalogs

DATA = Path(__file__).parents[1] / "data" / "locales"


def load(
    directories: list[Path], supported: list[str] = SUPPORTED, **kwargs: object
) -> CatalogStore:
    return CatalogStore.load(
        supported=[Locale.parse(tag) for tag in supported],
        default=Locale.parse(supported[0]),
        source=Locale.parse("en"),
        directories=directories,
        **kwargs,  # type: ignore[arg-type]
    )


def test_loads_every_supported_locale(catalog_dir: Path) -> None:
    store = load([catalog_dir])
    assert {locale.tag for locale in store.locales} == set(SUPPORTED)
    assert {"messages", "admin", "fastapi_locale"} <= store.domains


def test_fallback_chain_uses_shorter_tags(catalog_dir: Path) -> None:
    translator = load([catalog_dir]).translator_for("pt-BR")
    assert translator.gettext("Goodbye") == "Tchau"
    assert translator.gettext("Hello") == "Olá"


def test_fallback_chain_ends_at_the_default_locale(catalog_dir: Path) -> None:
    store = load([catalog_dir], supported=["de", "fr"])
    assert store.translator_for("fr").gettext("Item not found") == "Artikel nicht gefunden"


def test_later_directories_override_earlier_ones(catalog_dir: Path, tmp_path: Path) -> None:
    override = tmp_path / "override"
    messages = override / "de" / "LC_MESSAGES"
    messages.mkdir(parents=True)
    (messages / "messages.po").write_text(
        'msgid ""\nmsgstr ""\n"Content-Type: text/plain; charset=UTF-8\\n"\n\n'
        'msgid "Hello"\nmsgstr "Servus"\n',
        encoding="utf-8",
    )
    compile_catalogs(override, override)
    translator = load([catalog_dir, override]).translator_for("de")
    assert translator.gettext("Hello") == "Servus"
    assert translator.gettext("Hello {name}", name="Ana") == "Hallo Ana"


def test_application_catalog_overrides_builtin_errors(catalog_dir: Path) -> None:
    translator = load([catalog_dir]).translator_for("de")
    text = translator.dpgettext(
        "fastapi_locale", "greater_than", "Input should be greater than {gt}", gt=1
    )
    assert text == "Wert muss groesser als 1 sein (App)"


def test_builtin_errors_can_be_disabled(catalog_dir: Path) -> None:
    store = load([catalog_dir], supported=["en", "fr"], builtin=False)
    assert "fastapi_locale" not in store.domains


def test_locale_directories_are_matched_after_normalization(catalog_dir: Path) -> None:
    assert (
        load([catalog_dir], supported=["pt-br", "en"]).translator_for("pt-BR").gettext("Goodbye")
        == "Tchau"
    )


def test_unrelated_entries_are_ignored(tmp_path: Path) -> None:
    (tmp_path / "README.txt").write_text("not a locale", encoding="utf-8")
    (tmp_path / "not a tag").mkdir()
    (tmp_path / "de").mkdir()
    store = load([tmp_path], supported=["en", "de"])
    assert store.translator_for("de").gettext("Hello") == "Hello"


def test_missing_directory_fails(tmp_path: Path) -> None:
    with pytest.raises(CatalogLoadError, match="does not exist"):
        load([tmp_path / "missing"])


def test_corrupt_catalog_fails(tmp_path: Path) -> None:
    messages = tmp_path / "de" / "LC_MESSAGES"
    messages.mkdir(parents=True)
    (messages / "messages.mo").write_bytes(b"not a catalog")
    with pytest.raises(CatalogLoadError, match=r"messages\.mo"):
        load([tmp_path], supported=["en", "de"])


def test_corrupt_builtin_catalog_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    messages = tmp_path / "de" / "LC_MESSAGES"
    messages.mkdir(parents=True)
    (messages / "fastapi_locale.po").write_bytes(b'msgid "a"\nmsgstr[0] "b"\n\xff')
    monkeypatch.setattr("fastapi_locale._catalog.BUILTIN_DIRECTORY", tmp_path)
    with pytest.raises(CatalogLoadError, match="built-in catalog"):
        load([], supported=["en", "de"])


def test_warns_about_locales_without_catalogs(
    catalog_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="fastapi_locale"):
        load([catalog_dir], supported=["en", "de", "sw", "en-GB"])
    assert "sw" in caplog.text
    assert "en-GB" not in caplog.text


def test_match_uses_lookup(catalog_dir: Path) -> None:
    store = load([catalog_dir])
    assert store.match("hi-IN") == Locale.parse("hi")
    assert store.match("sw") is None
    assert store.match("../../etc/passwd") is None


def test_translator_for_rejects_unsupported(catalog_dir: Path) -> None:
    store = load([catalog_dir])
    assert store.translator_for(Locale.parse("de-AT")).locale.tag == "de"
    with pytest.raises(UnsupportedLocaleError, match=r"'sw' is not supported"):
        store.translator_for("sw")


def test_default_translator(catalog_dir: Path) -> None:
    assert load([catalog_dir]).default_translator.locale.tag == "en"


def test_match_cache_is_bounded(catalog_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("fastapi_locale._catalog._MATCH_CACHE_SIZE", 3)
    store = load([catalog_dir])
    for value in ("de", "fr", "hi", "ru", "de"):
        store.match(value)
    assert len(store._matches) <= 3
    assert store.match("de") == Locale.parse("de")


def test_no_warning_when_only_builtin_messages_are_used(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="fastapi_locale"):
        load([], supported=["en", "de"])
    assert not caplog.records


def test_source_language_does_not_fall_back_to_the_default_locale(catalog_dir: Path) -> None:
    store = load([catalog_dir], supported=["de", "en", "en-GB", "fr"])
    for tag in ("en", "en-GB"):
        translator = store.translator_for(tag)
        assert translator.gettext("Item not found") == "Item not found"
        assert (
            translator.dpgettext("fastapi_locale", "missing", "Field required") == "Field required"
        )
    assert store.translator_for("fr").gettext("Item not found") == "Artikel nicht gefunden"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("pt-BR", "pt-BR"),
        ("pt", "pt-BR"),
        ("pt-PT", "pt-BR"),
        ("zh", "zh-Hans"),
        ("zh-TW", "zh-Hans"),
        ("zh-Hans-CN", "zh-Hans"),
        ("zh-Hant-TW", None),
        ("sw", None),
    ],
)
def test_match_falls_back_to_another_region_of_the_language(
    value: str, expected: str | None
) -> None:
    matched = load([], supported=["en", "pt-BR", "zh-Hans"]).match(value)
    assert (matched.tag if matched else None) == expected


def test_lookup_is_preferred_over_another_region(catalog_dir: Path) -> None:
    store = load([catalog_dir])
    assert store.match("pt-PT") == Locale.parse("pt")


@pytest.mark.parametrize("supported", ["pt", "pt-PT", "pt-BR"])
def test_builtin_regional_catalog_serves_its_language(supported: str) -> None:
    translator = load([], supported=["en", supported]).translator_for(supported)
    assert (
        translator.dpgettext("fastapi_locale", "missing", "Field required") == "Campo obrigatório"
    )


def test_values_that_cannot_be_tags_are_refused_before_the_cache(catalog_dir: Path) -> None:
    store = load([catalog_dir])
    for value in (None, 5, b"de", "x" * 65, "de" + "-x" * 4000):
        assert store.match(value) is None
    assert store._matches == {}
    with pytest.raises(UnsupportedLocaleError, match="None is not supported"):
        store.translator_for(None)  # type: ignore[arg-type]


def damaged(data: bytes, kind: str) -> bytes:
    if kind == "empty":
        return b""
    if kind == "truncated":
        return data[:30]
    return data.replace(b"charset=utf-8", b"charset=xtf-9")


@pytest.mark.parametrize("kind", ["empty", "truncated", "unknown charset"])
def test_unreadable_catalogs_fail_with_the_file_name(tmp_path: Path, kind: str) -> None:
    messages = tmp_path / "de" / "LC_MESSAGES"
    messages.mkdir(parents=True)
    (messages / "messages.po").write_text(
        'msgid ""\nmsgstr ""\n"Content-Type: text/plain; charset=utf-8\\n"\n\n'
        'msgid "Hello"\nmsgstr "Hallo"\n',
        encoding="utf-8",
    )
    compile_catalogs(tmp_path, tmp_path)
    compiled = messages / "messages.mo"
    data = compiled.read_bytes()
    assert damaged(data, kind) != data
    compiled.write_bytes(damaged(data, kind))
    with pytest.raises(CatalogLoadError, match=r"messages\.mo"):
        load([tmp_path], supported=["en", "de"])
