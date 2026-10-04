from __future__ import annotations

import logging
from pathlib import Path

import pytest

from fastapi_locale import Locale, Translator
from fastapi_locale._catalog import CatalogStore
from tests.conftest import SUPPORTED


@pytest.fixture
def store(catalog_dir: Path) -> CatalogStore:
    return CatalogStore.load(
        supported=[Locale.parse(tag) for tag in SUPPORTED],
        default=Locale.parse("en"),
        source=Locale.parse("en"),
        directories=[catalog_dir],
    )


def tr(store: CatalogStore, tag: str) -> Translator:
    return store.translator_for(tag)


def test_gettext_and_placeholders(store: CatalogStore) -> None:
    assert tr(store, "de").gettext("Hello") == "Hallo"
    assert tr(store, "de").gettext("Hello {name}", name="Ana") == "Hallo Ana"
    assert tr(store, "en").gettext("Hello {name}", name="Ana") == "Hello Ana"


def test_missing_message_returns_msgid(store: CatalogStore) -> None:
    assert tr(store, "de").gettext("Not in any catalog") == "Not in any catalog"
    assert tr(store, "de").gettext("Untranslated") == "Untranslated"


@pytest.mark.parametrize(
    ("tag", "n", "expected"),
    [
        ("en", 1, "1 file"),
        ("en", 0, "0 files"),
        ("de", 1, "1 Datei"),
        ("de", 2, "2 Dateien"),
        ("fr", 0, "0 fichier"),
        ("fr", 2, "2 fichiers"),
        ("ru", 1, "1 файл"),
        ("ru", 3, "3 файла"),
        ("ru", 5, "5 файлов"),
        ("ru", 11, "11 файлов"),
        ("ru", 21, "21 файл"),
        ("ar", 0, "لا ملفات 0"),
        ("ar", 1, "ملف واحد 1"),
        ("ar", 2, "ملفان 2"),
        ("ar", 5, "5 ملفات"),
        ("ar", 11, "11 ملفا"),
        ("ar", 100, "100 ملف"),
        ("ja", 1, "1 ファイル"),
        ("ja", 7, "7 ファイル"),
    ],
)
def test_plural_forms_follow_each_language(
    store: CatalogStore, tag: str, n: int, expected: str
) -> None:
    assert tr(store, tag).ngettext("{n} file", "{n} files", n) == expected


def test_context_separates_messages(store: CatalogStore) -> None:
    de = tr(store, "de")
    assert de.pgettext("month", "May") == "Mai"
    assert de.pgettext("verb", "May") == "Darf"
    assert de.gettext("May") == "May"
    assert de.npgettext("month", "May", "Mays", 2) == "Mays"


def test_domains(store: CatalogStore) -> None:
    de = tr(store, "de")
    assert de.dgettext("admin", "Dashboard") == "Uebersicht"
    assert de.gettext("Dashboard") == "Dashboard"
    assert de.dgettext("unknown", "Dashboard") == "Dashboard"
    assert de.dngettext("messages", "{n} file", "{n} files", 2) == "2 Dateien"
    assert de.dpgettext("messages", "month", "May") == "Mai"
    assert de.dnpgettext("messages", "month", "May", "Mays", 1) == "May"


def test_explicit_n_param_wins(store: CatalogStore) -> None:
    assert tr(store, "en").ngettext("{n} file", "{n} files", 2, n="two") == "two files"


def test_broken_translation_placeholder_is_logged_once(
    store: CatalogStore, caplog: pytest.LogCaptureFixture
) -> None:
    de = tr(store, "de")
    with caplog.at_level(logging.WARNING, logger="fastapi_locale"):
        assert de.gettext("Broken {name}", name="x") == "Kaputt {wrong}"
        de.gettext("Broken {name}", name="x")
    assert caplog.text.count("placeholder {wrong}") == 1


def test_warning_memory_is_bounded(store: CatalogStore) -> None:
    en = tr(store, "en")
    for i in range(1500):
        en.gettext(f"Dynamic {{missing}} {i}", other=1)
    assert len(en._warned) == 1024


def test_properties(store: CatalogStore) -> None:
    de = tr(store, "de")
    assert de.locale == Locale.parse("de")
    assert de.default_domain == "messages"
    assert repr(de) == "Translator('de')"


def test_braces_are_handled_the_same_with_and_without_values(store: CatalogStore) -> None:
    en = tr(store, "en")
    assert en.gettext("Use {{braces}}") == "Use {braces}"
    assert en.gettext("Use {{braces}} {x}", x=1) == "Use {braces} 1"
    assert en.ngettext("{{one}}", "{{many}}", 2) == "{many}"
    assert en.gettext("100% {name}") == "100% {name}"


def test_plain_lookup_of_a_plural_entry_uses_the_form_for_one(store: CatalogStore) -> None:
    assert tr(store, "de").gettext("{n} file", n=1) == "1 Datei"
    assert tr(store, "ru").gettext("{n} file", n=1) == "1 файл"


@pytest.mark.parametrize("tag", ["en", "de"])
@pytest.mark.parametrize("n", ["3", 2.5])
def test_the_count_must_be_an_integer_in_every_locale(
    store: CatalogStore, tag: str, n: object
) -> None:
    with pytest.raises(TypeError, match="n must be an integer"):
        tr(store, tag).ngettext("{n} file", "{n} files", n)  # type: ignore[arg-type]


def test_find_returns_the_text_as_written(store: CatalogStore) -> None:
    de = tr(store, "de")
    assert de._find("Hello {name}") == "Hallo {name}"
    assert de._find("Not in any catalog") is None
    assert de._find("Untranslated") is None
