"""Implementation of the catalog commands, built on Babel's extraction and PO/MO support."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, TextIO

from babel.messages.catalog import Catalog, Message
from babel.messages.extract import extract_from_dir
from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po, write_po

from fastapi_locale._formatting import placeholders
from fastapi_locale._locale import Locale

if TYPE_CHECKING:
    from pathlib import Path

    from fastapi_locale.cli.settings import Settings

__all__ = ["KEYWORDS", "Report", "check", "compile_catalogs", "extract", "init", "update"]

# Argument positions of every translation function; "c" marks the message context.
KEYWORDS: dict[str, tuple[int | tuple[int, str], ...] | None] = {
    "_": None,
    "gettext": None,
    "gettext_lazy": None,
    "gettext_noop": None,
    "ngettext": (1, 2),
    "ngettext_lazy": (1, 2),
    "pgettext": ((1, "c"), 2),
    "pgettext_lazy": ((1, "c"), 2),
    "npgettext": ((1, "c"), 2, 3),
    "npgettext_lazy": ((1, "c"), 2, 3),
    "dgettext": (2,),
    "dngettext": (2, 3),
    "dpgettext": ((2, "c"), 3),
    "dnpgettext": ((2, "c"), 3, 4),
}
WIDTH = 100
MessageId = tuple[str | None, str]


@dataclass
class Report:
    """Problems found by a command; errors fail it, warnings do not."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def write(self, out: TextIO) -> None:
        """Print the problems."""
        for line in self.errors:
            out.write(f"error: {line}\n")
        for line in self.warnings:
            out.write(f"warning: {line}\n")


def extract_catalog(settings: Settings) -> Catalog:
    """Scan the source directories and return the template catalog."""
    catalog = Catalog(project=settings.root.name, fuzzy=False)
    for source in settings.sources:
        for filename, lineno, message, comments, context in extract_from_dir(
            source,
            method_map=[("**.py", "python")],
            keywords=KEYWORDS,
            comment_tags=("Translators:",),
            strip_comment_tags=True,
        ):
            location = (source / filename).relative_to(settings.root).as_posix()
            catalog.add(
                message,
                None,
                [(location, lineno)],
                auto_comments=comments,
                context=context,
            )
    return catalog


def extract(settings: Settings, out: TextIO) -> Report:
    """Write the template from the sources."""
    catalog = extract_catalog(settings)
    settings.template.parent.mkdir(parents=True, exist_ok=True)
    _write_po(settings.template, catalog)
    out.write(f"wrote {_show(settings, settings.template)} ({len(catalog)} messages)\n")
    return Report()


def init(settings: Settings, locale: str, out: TextIO) -> Report:
    """Create the catalog of a new language from the template."""
    parsed = Locale.try_parse(locale)
    if parsed is None:
        return Report(errors=[f"{locale!r} is not a valid language tag"])
    template = _read_template(settings)
    if template is None:
        return Report(errors=["no template yet; run extract first"])
    path = settings.catalog(parsed.tag.replace("-", "_"))
    if path.exists():
        return Report(errors=[f"{_show(settings, path)} already exists; use update"])
    # Not fuzzy: a fuzzy header is dropped on compile, and its Plural-Forms with it.
    catalog = Catalog(locale=parsed.tag.replace("-", "_"), domain=settings.domain, fuzzy=False)
    catalog.update(template)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_po(path, catalog)
    out.write(f"created {_show(settings, path)}\n")
    return Report()


def update(settings: Settings, out: TextIO) -> Report:
    """Merge the template into every catalog of the domain."""
    template = _read_template(settings)
    if template is None:
        return Report(errors=["no template yet; run extract first"])
    for path in settings.catalogs():
        catalog = _read_po(path)
        catalog.update(template, update_header_comment=False)
        _write_po(path, catalog)
        out.write(f"updated {_show(settings, path)}\n")
    return Report()


def compile_catalogs(settings: Settings, out: TextIO, *, strict: bool = False) -> Report:
    """Compile every catalog to ``.mo``; with ``strict``, fuzzy entries are errors."""
    report = Report()
    for path in settings.catalogs():
        catalog = _read_po(path)
        fuzzy = [message for message in catalog if message.id and message.fuzzy]
        if fuzzy:
            problem = f"{_show(settings, path)}: {len(fuzzy)} fuzzy entries not compiled"
            (report.errors if strict else report.warnings).append(problem)
            if strict:
                continue
        catalog.fuzzy = False  # always keep the header, which carries Plural-Forms
        with path.with_suffix(".mo").open("wb") as stream:
            write_mo(stream, catalog)
        out.write(f"compiled {_show(settings, path.with_suffix('.mo'))}\n")
    return report


def check(settings: Settings, *, require_complete: bool = False) -> Report:
    """Report stale, fuzzy, obsolete and broken entries without changing any file."""
    report = Report()
    extracted = extract_catalog(settings)
    wanted = {_message_id(message) for message in extracted if message.id}
    template = _read_template(settings)
    if template is None or {_message_id(m) for m in template if m.id} != wanted:
        report.errors.append(f"{_show(settings, settings.template)} is out of date; run extract")
    catalogs = settings.catalogs()
    if not catalogs:
        report.warnings.append(f"no catalogs for domain {settings.domain!r} yet")
    for path in catalogs:
        _check_catalog(settings, path, wanted, report, require_complete=require_complete)
    return report


def _check_catalog(
    settings: Settings,
    path: Path,
    wanted: set[MessageId],
    report: Report,
    *,
    require_complete: bool,
) -> None:
    name = _show(settings, path)
    if "Plural-Forms:" not in path.read_text(encoding="utf-8"):
        report.errors.append(f"{name}: no Plural-Forms header")
    catalog = _read_po(path)
    if catalog.fuzzy:
        report.errors.append(f"{name}: header is marked fuzzy")
    present = {_message_id(message) for message in catalog if message.id}
    for context, msgid in sorted(wanted - present, key=str):
        report.errors.append(f"{name}: missing {_describe(context, msgid)}; run update")
    for context, msgid in sorted(present - wanted, key=str):
        report.warnings.append(f"{name}: not in the sources any more: {_describe(context, msgid)}")
    for message in catalog:
        if not message.id:
            continue
        label = _describe(message.context, _message_id(message)[1])
        if message.fuzzy:
            report.errors.append(f"{name}: fuzzy {label}")
        translations = [s for s in _strings(message.string) if s]
        if not translations:
            (report.errors if require_complete else report.warnings).append(
                f"{name}: untranslated {label}"
            )
        allowed = frozenset().union(*(placeholders(s) for s in _strings(message.id)))
        if message.pluralizable:
            allowed |= {"n"}
        for translation in translations:
            unknown = placeholders(translation) - allowed
            if unknown:
                report.errors.append(f"{name}: {label} uses unknown placeholders {sorted(unknown)}")


def _message_id(message: Message) -> MessageId:
    msgid = message.id if isinstance(message.id, str) else message.id[0]
    return (message.context, msgid)


def _strings(value: str | tuple[str, ...] | list[str] | None) -> list[str]:
    if value is None:
        return []
    return [value] if isinstance(value, str) else list(value)


def _describe(context: str | None, msgid: str) -> str:
    return f"{msgid!r}" if context is None else f"{msgid!r} (context {context!r})"


def _read_template(settings: Settings) -> Catalog | None:
    return _read_po(settings.template) if settings.template.is_file() else None


def _read_po(path: Path) -> Catalog:
    with path.open("rb") as stream:
        return read_po(stream, locale=_locale_of(path))


def _locale_of(path: Path) -> str | None:
    if path.suffix == ".pot":
        return None
    return path.parent.parent.name


def _write_po(path: Path, catalog: Catalog) -> None:
    with path.open("wb") as stream:
        write_po(stream, catalog, width=WIDTH, sort_output=False, sort_by_file=True)


def _show(settings: Settings, path: Path) -> str:
    try:
        return path.relative_to(settings.root).as_posix()
    except ValueError:
        return str(path)
