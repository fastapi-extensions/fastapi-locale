"""Locale value object: BCP 47 tag parsing, normalization and RFC 4647 truncation."""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

import babel

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = ["MAX_TAG_LENGTH", "Locale"]

# Longer values are rejected before any parsing, so request input cannot cost more than this.
MAX_TAG_LENGTH = 64

_SUBTAG = re.compile(r"[A-Za-z0-9]{1,8}")
_LANGUAGE = re.compile(r"[A-Za-z]{2,3}|[A-Za-z]{5,8}")
_REGION_LETTERS = 2
_REGION_DIGITS = 3
_SCRIPT_LENGTH = 4


@dataclass(frozen=True, slots=True)
class Locale:
    """A language tag such as ``hi``, ``pt-BR`` or ``zh-Hant-TW``; create it with ``parse``."""

    tag: str
    language: str
    script: str | None = None
    region: str | None = None

    @classmethod
    def parse(cls, value: str) -> Locale:
        """Parse and normalize a tag; raise ``ValueError`` if it is not a valid language tag."""
        locale = cls.try_parse(value)
        if locale is None:
            msg = f"not a valid language tag: {value!r}"
            raise ValueError(msg)
        return locale

    @classmethod
    def try_parse(cls, value: str) -> Locale | None:
        """Parse and normalize a tag, or return ``None`` if it is not a valid language tag."""
        if len(value) > MAX_TAG_LENGTH:
            return None
        parts = value.strip().replace("_", "-").split("-")
        if not all(_SUBTAG.fullmatch(part) for part in parts):
            return None
        if not _LANGUAGE.fullmatch(parts[0]):
            return None

        normalized = [parts[0].lower()]
        script = region = None
        rest = parts[1:]
        if rest and len(rest[0]) == _SCRIPT_LENGTH and rest[0].isalpha():
            script = rest.pop(0).title()
            normalized.append(script)
        if rest and _is_region(rest[0]):
            region = rest.pop(0).upper()
            normalized.append(region)
        # Variants, extensions and private use subtags are kept, in lower case.
        normalized.extend(part.lower() for part in rest)
        return cls("-".join(normalized), normalized[0], script, region)

    def truncations(self) -> Iterator[Locale]:
        """Yield this locale, then ever shorter ones, following RFC 4647 section 3.4."""
        parts = self.tag.split("-")
        while parts:
            yield Locale.parse("-".join(parts))
            parts.pop()
            # A single-letter subtag introduces an extension and is dropped with it.
            while parts and len(parts[-1]) == 1:
                parts.pop()

    @property
    def text_direction(self) -> Literal["ltr", "rtl"]:
        """Writing direction of the language, from CLDR data."""
        return _text_direction(self.tag)

    def __str__(self) -> str:
        return self.tag


def _is_region(subtag: str) -> bool:
    return (len(subtag) == _REGION_LETTERS and subtag.isalpha()) or (
        len(subtag) == _REGION_DIGITS and subtag.isdigit()
    )


@functools.lru_cache(maxsize=256)
def _text_direction(tag: str) -> Literal["ltr", "rtl"]:
    try:
        direction = babel.Locale.parse(tag, sep="-").text_direction
    except (ValueError, babel.UnknownLocaleError):
        return "ltr"
    return "rtl" if direction == "rtl" else "ltr"
