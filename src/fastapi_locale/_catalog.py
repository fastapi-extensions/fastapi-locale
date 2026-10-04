"""Catalog store: loads gettext catalogs once and builds one translator per supported locale."""

from __future__ import annotations

import gettext
import io
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po

from fastapi_locale._locale import MAX_TAG_LENGTH, Locale, truncations
from fastapi_locale._translator import Catalog, MessageKey, Translator, english_plural
from fastapi_locale.exceptions import CatalogLoadError, UnsupportedLocaleError

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

__all__ = ["BUILTIN_DIRECTORY", "BUILTIN_DOMAIN", "CatalogStore"]

logger = logging.getLogger("fastapi_locale")

BUILTIN_DOMAIN = "fastapi_locale"
BUILTIN_DIRECTORY = Path(__file__).parent / "locales"
_MESSAGES_DIR = "LC_MESSAGES"
# Request input decides the keys, so the match cache is bounded and cleared when full.
_MATCH_CACHE_SIZE = 2048


class CatalogStore:
    """Read-only set of translators, one per supported locale."""

    __slots__ = ("_default", "_domains", "_matches", "_translators")

    def __init__(
        self,
        translators: Mapping[str, Translator],
        default: Locale,
        domains: Iterable[str],
    ) -> None:
        self._translators = dict(translators)
        self._default = default
        self._domains = frozenset(domains)
        self._matches: dict[str, Locale | None] = {}

    @classmethod
    def load(
        cls,
        *,
        supported: Sequence[Locale],
        default: Locale,
        source: Locale,
        directories: Sequence[Path],
        builtin: bool = True,
        default_domain: str = "messages",
    ) -> CatalogStore:
        """Load catalogs for the supported locales; raise ``CatalogLoadError`` on any failure."""
        wanted = {
            truncated.tag for locale in (*supported, default) for truncated in truncations(locale)
        }
        catalogs: dict[tuple[str, str], Catalog] = {}
        if builtin:
            for catalog in _load_builtin(wanted):
                _merge_into(catalogs, catalog)
        for directory in directories:
            for catalog in _load_directory(directory, wanted):
                _merge_into(catalogs, catalog)

        domains = {domain for _, domain in catalogs} | {default_domain}
        translators = {
            locale.tag: Translator(
                locale,
                {domain: _chain(catalogs, locale, default, source, domain) for domain in domains},
                default_domain,
            )
            for locale in supported
        }
        _report(catalogs, supported, source, default_domain, directories)
        return cls(translators, default, domains)

    @property
    def default_translator(self) -> Translator:
        """Translator for the default locale."""
        return self._translators[self._default.tag]

    @property
    def locales(self) -> frozenset[Locale]:
        """Supported locales."""
        return frozenset(translator.locale for translator in self._translators.values())

    @property
    def domains(self) -> frozenset[str]:
        """Domains that have at least one catalog, plus the default domain."""
        return self._domains

    def match(self, value: object) -> Locale | None:
        """Return the supported locale that serves a language range, if any.

        RFC 4647 lookup comes first: the range itself, then ever shorter prefixes. When that finds
        nothing, the first supported locale in the same language is used, so ``pt`` and ``pt-PT``
        both reach ``pt-BR``.
        """
        # Request input: anything that cannot be a tag is refused before it reaches the cache.
        if not isinstance(value, str) or len(value) > MAX_TAG_LENGTH:
            return None
        try:
            return self._matches[value]
        except KeyError:
            pass
        result = self._lookup(value)
        if len(self._matches) >= _MATCH_CACHE_SIZE:
            self._matches.clear()
        self._matches[value] = result
        return result

    def _lookup(self, value: str) -> Locale | None:
        locale = Locale.try_parse(value)
        if locale is None:
            return None
        for candidate in truncations(locale):
            translator = self._translators.get(candidate.tag)
            if translator is not None:
                return translator.locale
        for translator in self._translators.values():
            supported = translator.locale
            # Another region of the language is closer than the default locale. Another
            # script is not, so an explicitly requested script is never crossed.
            if supported.language == locale.language and (
                locale.script is None or supported.script in {None, locale.script}
            ):
                return supported
        return None

    def translator_for(self, locale: str | Locale) -> Translator:
        """Return the translator for a locale; raise ``UnsupportedLocaleError`` if none matches."""
        tag = locale.tag if isinstance(locale, Locale) else locale
        matched = self.match(tag)
        if matched is None:
            msg = (
                f"locale {tag!r} is not supported; "
                f"supported locales are {sorted(self._translators)}"
            )
            raise UnsupportedLocaleError(msg)
        return self._translators[matched.tag]


def _chain(
    catalogs: Mapping[tuple[str, str], Catalog],
    locale: Locale,
    default: Locale,
    source: Locale,
    domain: str,
) -> tuple[Catalog, ...]:
    candidates = list(truncations(locale))
    # Messages in the source language are the msgids themselves. Falling through to the default
    # locale's catalog would answer in another language, so the chain stops here.
    if locale.language != source.language:
        candidates.extend(truncations(default))
    chain: list[Catalog] = []
    for candidate in candidates:
        catalog = catalogs.get((candidate.tag, domain))
        if catalog is not None and catalog not in chain:
            chain.append(catalog)
    return tuple(chain)


def _merge_into(catalogs: dict[tuple[str, str], Catalog], catalog: Catalog) -> None:
    """Add a catalog; a later catalog for the same locale and domain overrides earlier entries."""
    key = (catalog.locale, catalog.domain)
    existing = catalogs.get(key)
    if existing is None:
        catalogs[key] = catalog
        return
    catalogs[key] = Catalog(
        locale=catalog.locale,
        domain=catalog.domain,
        messages={**existing.messages, **catalog.messages},
        plural=catalog.plural,
        sources=(*existing.sources, *catalog.sources),
    )


def _locale_directories(directory: Path) -> list[tuple[str, Path]]:
    """List the locales found in a catalog directory with their ``LC_MESSAGES`` directories."""
    try:
        children = sorted(directory.iterdir())
    except OSError as exc:
        msg = f"cannot read catalog directory {directory}: {exc}"
        raise CatalogLoadError(msg) from exc
    found: list[tuple[str, Path]] = []
    for child in children:
        locale = Locale.try_parse(child.name) if child.is_dir() else None
        if locale is not None:
            found.append((locale.tag, child / _MESSAGES_DIR))
    return found


def _load_directory(directory: Path, wanted: set[str]) -> Iterable[Catalog]:
    if not directory.is_dir():
        msg = f"catalog directory does not exist: {directory}"
        raise CatalogLoadError(msg)
    for tag, messages_dir in _locale_directories(directory):
        if tag not in wanted or not messages_dir.is_dir():
            continue
        for path in sorted(messages_dir.glob("*.mo")):
            yield _from_gnu(tag, path.stem, _read_mo(path), str(path))


def _read_mo(path: Path) -> gettext.GNUTranslations:
    try:
        with path.open("rb") as stream:
            return gettext.GNUTranslations(stream)
    except Exception as exc:
        # The parser fails in many ways (OSError, struct.error, LookupError for an unknown
        # charset, ValueError for a bad plural rule); each one means the file is unusable.
        msg = f"cannot read catalog {path}: {exc}"
        raise CatalogLoadError(msg) from exc


def _load_builtin(wanted: set[str]) -> Iterable[Catalog]:
    directories = _locale_directories(BUILTIN_DIRECTORY)
    shipped = {tag for tag, _ in directories}
    served: set[str] = set()
    for tag, messages_dir in directories:
        path = messages_dir / f"{BUILTIN_DOMAIN}.po"
        if not path.is_file():
            continue
        targets = [tag] if tag in wanted else []
        # A regional catalog also serves its bare language when none ships for that language,
        # so an application that supports "pt" or "pt-PT" still gets the "pt-BR" messages.
        language = tag.partition("-")[0]
        if language in wanted and language not in shipped and language not in served:
            targets.append(language)
            served.add(language)
        if not targets:
            continue
        translations = _read_builtin(path, tag)
        for target in targets:
            yield _from_gnu(target, BUILTIN_DOMAIN, translations, str(path))


def _read_builtin(path: Path, tag: str) -> gettext.GNUTranslations:
    try:
        with path.open("rb") as stream:
            catalog = read_po(stream, locale=tag.replace("-", "_"), domain=BUILTIN_DOMAIN)
        buffer = io.BytesIO()
        write_mo(buffer, catalog)
        buffer.seek(0)
        return gettext.GNUTranslations(buffer)
    except Exception as exc:
        msg = f"cannot read built-in catalog {path}: {exc}"
        raise CatalogLoadError(msg) from exc


def _from_gnu(tag: str, domain: str, translations: gettext.GNUTranslations, source: str) -> Catalog:
    # GNUTranslations keeps its parsed messages in _catalog; this is the one place that reads it.
    raw: dict[MessageKey, str] = dict(getattr(translations, "_catalog", {}))
    raw.pop("", None)  # the header entry
    plural = getattr(translations, "plural", None)
    return Catalog(
        locale=tag,
        domain=domain,
        messages=raw,
        plural=plural if callable(plural) else english_plural,
        sources=(source,),
    )


def _report(
    catalogs: Mapping[tuple[str, str], Catalog],
    supported: Sequence[Locale],
    source: Locale,
    default_domain: str,
    directories: Sequence[Path],
) -> None:
    logger.info(
        "Loaded %d catalogs (%d messages) for locales %s from %s",
        len(catalogs),
        sum(len(catalog.messages) for catalog in catalogs.values()),
        ", ".join(locale.tag for locale in supported),
        ", ".join(str(directory) for directory in directories) or "no application directories",
    )
    if not directories:
        return  # only built-in error messages are wanted; missing app catalogs are expected
    for locale in supported:
        if locale.language == source.language:
            continue
        if not any((t.tag, default_domain) in catalogs for t in truncations(locale)):
            logger.warning(
                "No %r catalog found for supported locale %s; messages will not be translated",
                default_domain,
                locale.tag,
            )
