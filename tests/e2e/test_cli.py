from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
from babel.messages.pofile import read_po, write_po

from fastapi_locale import LocaleConfig, Localization, use_locale

Cli = Callable[..., subprocess.CompletedProcess[str]]

PYPROJECT = """
[tool.fastapi-locale]
sources = ["app"]
locales_dir = "app/locales"
"""
CODE = """
from fastapi_locale import gettext, gettext_lazy, ngettext, pgettext

TITLE = gettext_lazy("Orders")

def summary(n):
    # Translators: shown on the dashboard
    return ngettext("{n} order", "{n} orders", n)

def month():
    return pgettext("month", "May")
"""


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text(PYPROJECT, encoding="utf-8")
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "views.py").write_text(CODE, encoding="utf-8")
    return tmp_path


def translate(path: Path, table: dict[str, str | tuple[str, ...]]) -> None:
    with path.open("rb") as stream:
        catalog = read_po(stream, locale="ru")
    for message in catalog:
        key = message.id if isinstance(message.id, str) else message.id[0]
        if key in table:
            message.string = table[key]
    with path.open("wb") as stream:
        write_po(stream, catalog)


def test_full_workflow(project: Path, cli: Cli) -> None:
    extract = cli("extract", cwd=project)
    assert extract.returncode == 0, extract.stderr
    assert "3 messages" in extract.stdout
    template = (project / "app/locales/messages.pot").read_text(encoding="utf-8")
    assert "Translators: shown on the dashboard" not in template
    assert "shown on the dashboard" in template
    assert 'msgctxt "month"' in template

    assert cli("init", "--locale", "ru", cwd=project).returncode == 0
    po = project / "app/locales/ru/LC_MESSAGES/messages.po"
    assert "nplurals=3" in po.read_text(encoding="utf-8")

    strict = cli("check", "--require-complete", cwd=project)
    assert strict.returncode == 1
    assert "untranslated 'Orders'" in strict.stdout

    translate(
        po,
        {
            "Orders": "Заказы",
            "{n} order": ("{n} заказ", "{n} заказа", "{n} заказов"),
            "May": "Май",
        },
    )
    assert cli("check", "--require-complete", cwd=project).returncode == 0

    views = project / "app" / "views.py"
    views.write_text(
        views.read_text(encoding="utf-8") + '\nNEW = gettext("Refund")\n', encoding="utf-8"
    )
    stale = cli("check", cwd=project)
    assert stale.returncode == 1
    assert "out of date; run extract" in stale.stdout
    assert cli("extract", cwd=project).returncode == 0
    missing = cli("check", cwd=project)
    assert "missing 'Refund'" in missing.stdout
    assert cli("update", cwd=project).returncode == 0
    assert cli("check", cwd=project).returncode == 0

    compiled = cli("compile", cwd=project)
    assert compiled.returncode == 0, compiled.stdout
    localization = Localization(
        LocaleConfig(
            default_locale="en",
            supported_locales=["en", "ru"],
            catalog_dirs=[project / "app/locales"],
        )
    )
    localization.make_default()
    with use_locale("ru") as translator:
        assert translator.ngettext("{n} order", "{n} orders", 5) == "5 заказов"
        assert translator.pgettext("month", "May") == "Май"


def test_check_finds_broken_catalogs(project: Path, cli: Cli) -> None:
    cli("extract", cwd=project)
    cli("init", "--locale", "ru", cwd=project)
    po = project / "app/locales/ru/LC_MESSAGES/messages.po"
    translate(po, {"Orders": "Заказы {count}"})
    with po.open("rb") as stream:
        catalog = read_po(stream, locale="ru")
    catalog["Orders"].flags.add("fuzzy")
    catalog.fuzzy = True
    with po.open("wb") as stream:
        write_po(stream, catalog)
    text = po.read_text(encoding="utf-8").replace('"Plural-Forms:', '"X-Removed:')
    po.write_text(text, encoding="utf-8")

    report = cli("check", cwd=project)
    assert report.returncode == 1
    assert "no Plural-Forms header" in report.stdout
    assert "header is marked fuzzy" in report.stdout
    assert "fuzzy 'Orders'" in report.stdout
    assert "unknown placeholders ['count']" in report.stdout

    strict = cli("compile", "--strict", cwd=project)
    assert strict.returncode == 1
    assert not po.with_suffix(".mo").exists()
    lenient = cli("compile", cwd=project)
    assert lenient.returncode == 0
    assert "fuzzy entries not compiled" in lenient.stdout


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (("init", "--locale", "not a tag"), "not a valid language tag"),
        (("update",), "no template yet"),
        (("init", "--locale", "de"), "no template yet"),
    ],
)
def test_usage_problems(project: Path, cli: Cli, args: tuple[str, ...], message: str) -> None:
    result = cli(*args, cwd=project)
    assert result.returncode == 1
    assert message in result.stdout


def test_init_refuses_to_overwrite(project: Path, cli: Cli) -> None:
    cli("extract", cwd=project)
    assert cli("init", "--locale", "de", cwd=project).returncode == 0
    again = cli("init", "--locale", "de", cwd=project)
    assert again.returncode == 1
    assert "already exists" in again.stdout


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (None, "not found"),
        ("not = [valid", "not valid TOML"),
        ("[project]\nname = 'x'\n", "no [tool.fastapi-locale] section"),
        ("[tool.fastapi-locale]\nsources = 'app'\n", "lists of strings"),
        ("[tool.fastapi-locale]\nlocales_dir = 1\n", "locales_dir must be a string"),
    ],
)
def test_configuration_errors(tmp_path: Path, cli: Cli, content: str | None, message: str) -> None:
    if content is not None:
        (tmp_path / "pyproject.toml").write_text(content, encoding="utf-8")
    result = cli("check", cwd=tmp_path)
    assert result.returncode == 2
    assert message in result.stderr


def test_check_without_catalogs_warns(project: Path, cli: Cli) -> None:
    cli("extract", cwd=project)
    result = cli("check", cwd=project)
    assert result.returncode == 0
    assert "no catalogs for domain 'messages' yet" in result.stdout
