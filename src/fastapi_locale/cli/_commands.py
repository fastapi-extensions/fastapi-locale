"""Implementation of the catalog commands, built on Babel's extraction and PO/MO support."""

from __future__ import annotations

import io
import os
import tokenize
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, TextIO, cast

from babel.messages.catalog import Catalog, Message
from babel.messages.extract import extract_python
from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po, write_po
from babel.util import LOCALTZ

from fastapi_locale._formatting import placeholders
from fastapi_locale._locale import Locale
from fastapi_locale.cli._settings import DOMAIN

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fastapi_locale.cli._settings import Settings

__all__ = ["FUNCTIONS", "Report", "check", "compile_catalogs", "extract", "init", "update"]


@dataclass(frozen=True, slots=True)
class Call:
    """Argument positions, counted from 1, of one translation function."""

    msgid: int = 1
    plural: int | None = None
    context: int | None = None
    domain: int | None = None


_EAGER = {
    "gettext": Call(),
    "ngettext": Call(1, plural=2),
    "pgettext": Call(2, context=1),
    "npgettext": Call(2, plural=3, context=1),
    "dgettext": Call(2, domain=1),
    "dngettext": Call(2, plural=3, domain=1),
    "dpgettext": Call(3, context=2, domain=1),
    "dnpgettext": Call(3, plural=4, context=2, domain=1),
}
# Every function the extractor recognizes; a lazy variant takes the arguments of its eager one.
FUNCTIONS: dict[str, Call] = {
    "_": Call(),
    "gettext_noop": Call(),
    **_EAGER,
    **{f"{name}_lazy": call for name, call in _EAGER.items()},
}
COMMENT_TAG = "Translators:"
WIDTH = 100
MessageId = tuple[str | None, str]
# Line, function name, its arguments (one value or a tuple; None where not a literal), comments.
_ExtractedCall = tuple[int, str, object, list[str]]
# Never part of an application's own sources, whatever the source directories are.
_SKIPPED_DIRECTORIES = frozenset({"__pycache__", "node_modules", "site-packages"})


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


def extract_catalogs(settings: Settings, report: Report) -> dict[str, Catalog]:
    """Scan the sources and return one template catalog per domain, the default one always."""
    catalogs = {settings.default_domain: _new_template(settings)}
    for path in _python_files(settings):
        location = _show(settings, path)
        try:
            with path.open("rb") as stream:
                found = list(extract_python(stream, dict.fromkeys(FUNCTIONS), (COMMENT_TAG,), {}))
        except (SyntaxError, tokenize.TokenError, UnicodeDecodeError) as exc:
            report.errors.append(f"{location}: cannot be read as Python: {exc}")
            continue
        # Babel annotates this extractor with the result type of its higher-level API.
        for lineno, function, arguments, comments in cast("list[_ExtractedCall]", found):
            call = FUNCTIONS[function]
            values = arguments if isinstance(arguments, tuple) else (arguments,)
            msgid = _literal(values, call.msgid)
            plural = _literal(values, call.plural)
            context = _literal(values, call.context)
            if not msgid or (call.plural and plural is None) or (call.context and context is None):
                continue  # not string literals, so there is no message to record
            domain = _literal(values, call.domain) if call.domain else settings.default_domain
            if domain is None or not DOMAIN.fullmatch(domain):
                report.warnings.append(
                    f"{location}:{lineno}: {function}() needs a literal domain name; "
                    "message skipped"
                )
                continue
            if domain not in catalogs:
                catalogs[domain] = _new_template(settings)
            catalogs[domain].add(
                msgid if plural is None else (msgid, plural),
                None,
                [(location, lineno)],
                auto_comments=[comment.removeprefix(COMMENT_TAG).strip() for comment in comments],
                context=context,
            )
    return catalogs


def extract(settings: Settings, out: TextIO) -> Report:
    """Write one template per domain from the sources."""
    report = Report()
    catalogs = extract_catalogs(settings, report)
    # A domain that lost its last message keeps a template, now empty, so catalogs can follow.
    for path in settings.templates():
        catalogs.setdefault(path.stem, _new_template(settings))
    settings.catalog_dir.mkdir(parents=True, exist_ok=True)
    for domain in sorted(catalogs):
        path = settings.template(domain)
        count = len(catalogs[domain])
        noun = "message" if count == 1 else "messages"
        verb = "wrote" if _write_template(path, catalogs[domain]) else "unchanged"
        out.write(f"{verb} {_show(settings, path)} ({count} {noun})\n")
    return report


def init(settings: Settings, locale: str, out: TextIO) -> Report:
    """Create the catalogs of a new language from the templates."""
    parsed = Locale.try_parse(locale)
    if parsed is None:
        return Report(errors=[f"{locale!r} is not a valid language tag"])
    templates = settings.templates()
    if not templates:
        return Report(errors=["no template yet; run extract first"])
    report = Report()
    directory = parsed.tag.replace("-", "_")
    existing: list[str] = []
    for template in templates:
        path = settings.catalog(directory, template.stem)
        if path.exists():
            existing.append(f"{_show(settings, path)} already exists; use update")
            continue
        # Not fuzzy: a fuzzy header is dropped on compile, and its Plural-Forms with it.
        catalog = Catalog(locale=directory, domain=template.stem, fuzzy=False)
        catalog.update(_read_po(template))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_render(catalog))
        out.write(f"created {_show(settings, path)}\n")
        if catalog.locale is None:
            report.warnings.append(
                f"{_show(settings, path)}: no plural rule is known for {parsed.tag!r}; "
                "add a Plural-Forms header by hand"
            )
    if len(existing) == len(templates):
        report.errors.extend(existing)
    return report


def update(settings: Settings, out: TextIO) -> Report:
    """Merge each template into every catalog of its domain."""
    templates = settings.templates()
    if not templates:
        return Report(errors=["no template yet; run extract first"])
    for template_path in templates:
        template = _read_po(template_path)
        for path in settings.catalogs(template_path.stem):
            catalog = _read_po(path)
            catalog.update(template, update_header_comment=False)
            path.write_bytes(_render(catalog))
            out.write(f"updated {_show(settings, path)}\n")
    return Report()


def compile_catalogs(settings: Settings, out: TextIO, *, strict: bool = False) -> Report:
    """Compile the catalogs of every domain; with ``strict``, fuzzy entries are errors."""
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
    extracted = extract_catalogs(settings, report)
    domains = set(extracted) | {path.stem for path in settings.templates()}
    for domain in sorted(domains):
        wanted = _ids(extracted.get(domain))
        template = settings.template(domain)
        if not template.is_file() or _ids(_read_po(template)) != wanted:
            report.errors.append(f"{_show(settings, template)} is out of date; run extract")
        catalogs = settings.catalogs(domain)
        if not catalogs:
            report.warnings.append(f"no catalogs for domain {domain!r} yet")
        for path in catalogs:
            _check_catalog(settings, path, wanted, report, require_complete=require_complete)
    # Catalogs without a template, such as overrides of the library's own messages, are still
    # checked for everything that does not need the sources.
    for path in settings.catalogs():
        if path.stem not in domains:
            _check_catalog(settings, path, None, report, require_complete=require_complete)
    return report


def _check_catalog(
    settings: Settings,
    path: Path,
    wanted: set[MessageId] | None,
    report: Report,
    *,
    require_complete: bool,
) -> None:
    name = _show(settings, path)
    if b"Plural-Forms:" not in path.read_bytes():
        report.errors.append(f"{name}: no Plural-Forms header")
    catalog = _read_po(path)
    if catalog.fuzzy:
        report.errors.append(f"{name}: header is marked fuzzy")
    if wanted is not None:
        present = _ids(catalog)
        for context, msgid in sorted(wanted - present, key=str):
            report.errors.append(f"{name}: missing {_describe(context, msgid)}; run update")
        for context, msgid in sorted(present - wanted, key=str):
            report.warnings.append(
                f"{name}: not in the sources any more: {_describe(context, msgid)}"
            )
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


def _python_files(settings: Settings) -> Iterator[Path]:
    """Yield the Python files under the source directories in a stable order."""
    for source in settings.sources:
        for directory, subdirectories, files in os.walk(source):
            here = Path(directory)
            subdirectories[:] = sorted(
                name for name in subdirectories if not _skipped(settings, here / name)
            )
            for name in sorted(files):
                if name.endswith(".py") and not _excluded(settings, here / name):
                    yield here / name


def _skipped(settings: Settings, directory: Path) -> bool:
    """Hidden directories, caches, virtual environments and excluded paths are not scanned."""
    name = directory.name
    return (
        name.startswith(".")
        or name in _SKIPPED_DIRECTORIES
        or (directory / "pyvenv.cfg").is_file()
        or _excluded(settings, directory)
    )


def _excluded(settings: Settings, path: Path) -> bool:
    relative = Path(_show(settings, path))
    return any(relative.match(pattern) for pattern in settings.exclude)


def _literal(values: tuple[object, ...], position: int | None) -> str | None:
    """Return the argument at a position if the call passes a string literal there."""
    if position is None or position > len(values):
        return None
    value = values[position - 1]
    return value if isinstance(value, str) else None


def _new_template(settings: Settings) -> Catalog:
    return Catalog(project=settings.root.name, fuzzy=False)


def _write_template(path: Path, catalog: Catalog) -> bool:
    """Write a template unless only its creation date would change; say whether it was written."""
    if path.is_file():
        catalog.creation_date = _read_po(path).creation_date
        if _render(catalog) == path.read_bytes():
            return False
        catalog.creation_date = datetime.now(LOCALTZ)
    path.write_bytes(_render(catalog))
    return True


def _ids(catalog: Catalog | None) -> set[MessageId]:
    return {_message_id(message) for message in catalog or () if message.id}


def _message_id(message: Message) -> MessageId:
    msgid = message.id if isinstance(message.id, str) else message.id[0]
    return (message.context, msgid)


def _strings(value: str | tuple[str, ...] | list[str] | None) -> list[str]:
    if value is None:
        return []
    return [value] if isinstance(value, str) else list(value)


def _describe(context: str | None, msgid: str) -> str:
    return f"{msgid!r}" if context is None else f"{msgid!r} (context {context!r})"


def _read_po(path: Path) -> Catalog:
    with path.open("rb") as stream:
        return read_po(stream, locale=_locale_of(path))


def _locale_of(path: Path) -> str | None:
    if path.suffix == ".pot":
        return None
    return path.parent.parent.name


def _render(catalog: Catalog) -> bytes:
    buffer = io.BytesIO()
    write_po(buffer, catalog, width=WIDTH, sort_output=False, sort_by_file=True)
    return buffer.getvalue()


def _show(settings: Settings, path: Path) -> str:
    try:
        return path.relative_to(settings.root).as_posix()
    except ValueError:
        return str(path)
