from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
from babel.messages.pofile import read_po, write_po

import fastapi_locale
from fastapi_locale import LocaleConfig, Localization

Cli = Callable[..., subprocess.CompletedProcess[str]]

PYPROJECT = """
[tool.fastapi-locale]
sources = ["app"]
catalog_dir = "app/locales"
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
DOMAINS = """
from fastapi_locale import dgettext, dgettext_lazy, dngettext, gettext

TITLE = gettext("Orders")
PANEL = dgettext("admin", "Dashboard")
MENU = dgettext_lazy("admin", "Settings")

def users(n):
    return dngettext("admin", "{n} user", "{n} users", n)

def dynamic(domain):
    return dgettext(domain, "Chosen at run time")

OUTSIDE = dgettext("../outside", "Not a domain name")
"""
OVERRIDE = """
msgid ""
msgstr ""
"Content-Type: text/plain; charset=utf-8\\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\\n"

msgctxt "greater_than"
msgid "Input should be greater than {gt}"
msgstr "Mehr als {gt} bitte"
"""


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text(PYPROJECT, encoding="utf-8")
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "views.py").write_text(CODE, encoding="utf-8")
    return tmp_path


def translate(path: Path, table: dict[str, str | tuple[str, ...]]) -> None:
    with path.open("rb") as stream:
        catalog = read_po(stream, locale=path.parent.parent.name)
    for message in catalog:
        key = message.id if isinstance(message.id, str) else message.id[0]
        if key in table:
            message.string = table[key]
    with path.open("wb") as stream:
        write_po(stream, catalog)


def test_full_workflow(project: Path, cli: Cli) -> None:
    extract = cli("extract", cwd=project)
    assert extract.returncode == 0, extract.stderr
    assert "wrote app/locales/messages.pot (3 messages)" in extract.stdout
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
    translator = localization.translator("ru")
    assert translator.ngettext("{n} order", "{n} orders", 5) == "5 заказов"
    assert translator.pgettext("month", "May") == "Май"


def test_extract_leaves_an_unchanged_template_alone(project: Path, cli: Cli) -> None:
    cli("extract", cwd=project)
    template = project / "app/locales/messages.pot"
    lines = template.read_text(encoding="utf-8").splitlines(keepends=True)
    dated = [
        '"POT-Creation-Date: 2020-01-01 00:00+0000\\n"\n'
        if line.startswith('"POT-Creation-Date')
        else line
        for line in lines
    ]
    template.write_text("".join(dated), encoding="utf-8")
    before = template.read_bytes()

    again = cli("extract", cwd=project)
    assert "unchanged app/locales/messages.pot (3 messages)" in again.stdout
    assert template.read_bytes() == before


def test_each_domain_has_its_own_template_and_catalogs(project: Path, cli: Cli) -> None:
    views = project / "app" / "views.py"
    views.write_text(DOMAINS, encoding="utf-8")
    extract = cli("extract", cwd=project)
    assert extract.returncode == 0
    assert "wrote app/locales/admin.pot (3 messages)" in extract.stdout
    assert "wrote app/locales/messages.pot (1 message)" in extract.stdout
    assert extract.stdout.count("needs a literal domain name") == 2
    assert sorted(path.name for path in (project / "app/locales").iterdir()) == [
        "admin.pot",
        "messages.pot",
    ]
    assert "Dashboard" not in (project / "app/locales/messages.pot").read_text(encoding="utf-8")

    created = cli("init", "--locale", "de", cwd=project)
    assert created.stdout.count("created") == 2
    messages = project / "app/locales/de/LC_MESSAGES"
    translate(messages / "admin.po", {"Dashboard": "Uebersicht"})
    (messages / "fastapi_locale.po").write_text(OVERRIDE, encoding="utf-8")

    assert cli("check", cwd=project).returncode == 0
    assert cli("compile", cwd=project).returncode == 0
    assert sorted(path.name for path in messages.glob("*.mo")) == [
        "admin.mo",
        "fastapi_locale.mo",
        "messages.mo",
    ]
    config = LocaleConfig(
        default_locale="en", supported_locales=["en", "de"], catalog_dirs=[project / "app/locales"]
    )
    german = Localization(config).translator("de")
    assert german.dgettext("admin", "Dashboard") == "Uebersicht"
    override = german.dpgettext(
        "fastapi_locale", "greater_than", "Input should be greater than {gt}", gt=1
    )
    assert override == "Mehr als 1 bitte"

    # A domain that loses its last message keeps an empty template, so its catalogs can follow.
    views.write_text('from fastapi_locale import gettext\nTITLE = gettext("Orders")\n', "utf-8")
    assert "admin.pot (0 messages)" in cli("extract", cwd=project).stdout
    assert cli("check", cwd=project).returncode == 0


def test_only_application_sources_are_scanned(tmp_path: Path, cli: Cli) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[tool.fastapi-locale]\nexclude = ["tests", "*_generated.py"]\n', encoding="utf-8"
    )
    files = {
        "app.py": "App",
        "_internal/module.py": "Internal",
        "venv/lib/package.py": "Virtual environment",
        ".hidden/module.py": "Hidden",
        "node_modules/module.py": "Node",
        "pkg/tests/test_app.py": "Excluded directory",
        "pkg/api_generated.py": "Excluded file",
    }
    for name, message in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'from fastapi_locale import gettext\nX = gettext("{message}")\n', "utf-8")
    (tmp_path / "venv" / "pyvenv.cfg").write_text("home = /usr/bin\n", encoding="utf-8")

    result = cli("extract", cwd=tmp_path)
    assert "wrote locales/messages.pot (2 messages)" in result.stdout
    template = (tmp_path / "locales/messages.pot").read_text(encoding="utf-8")
    assert 'msgid "App"' in template
    assert 'msgid "Internal"' in template


def test_source_that_is_not_python_is_reported(project: Path, cli: Cli) -> None:
    (project / "app" / "broken.py").write_text('X = gettext("Never closed"\n', encoding="utf-8")
    result = cli("extract", cwd=project)
    assert result.returncode == 1
    assert "app/broken.py: cannot be read as Python" in result.stdout
    assert "(3 messages)" in result.stdout


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


def test_init_warns_when_no_plural_rule_is_known(project: Path, cli: Cli) -> None:
    cli("extract", cwd=project)
    result = cli("init", "--locale", "xx", cwd=project)
    assert result.returncode == 0
    assert "no plural rule is known for 'xx'" in result.stdout


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (None, "not found"),
        ("not = [valid", "not valid TOML"),
        ("[project]\nname = 'x'\n", "no [tool.fastapi-locale] section"),
        ("[tool.fastapi-locale]\nsources = 'app'\n", "lists of strings"),
        ("[tool.fastapi-locale]\ncatalog_dir = 1\n", "catalog_dir must be a string"),
        ("[tool.fastapi-locale]\ndefault_domain = 'a/b'\n", "default_domain must be a name"),
        ("[tool.fastapi-locale]\nlocales_dir = 'x'\n", "unknown setting 'locales_dir'"),
        ("[tool.fastapi-locale]\nsources = ['missing']\n", "sources entry is not a directory"),
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


def test_version(tmp_path: Path, cli: Cli) -> None:
    result = cli("--version", cwd=tmp_path)
    assert result.returncode == 0
    assert result.stdout.strip() == f"fastapi-locale {fastapi_locale.__version__}"
