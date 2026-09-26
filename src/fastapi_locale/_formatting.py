"""Named placeholder substitution for translated messages (ADR-0007)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

__all__ = ["format_message", "placeholders"]

_TOKEN = re.compile(r"\{\{|\}\}|\{([A-Za-z_][A-Za-z0-9_]*)\}")


def format_message(
    template: str,
    params: Mapping[str, object],
    on_missing: Callable[[str], None] | None = None,
) -> str:
    """Replace ``{name}`` with ``str(params[name])`` and ``{{``/``}}`` with literal braces.

    Nothing else is interpreted, so a translation cannot read attributes or items of its values.
    A name without a value is left as written and reported to ``on_missing``.
    """

    def replace(match: re.Match[str]) -> str:
        matched = match.group(0)
        if matched == "{{":
            return "{"
        if matched == "}}":
            return "}"
        name = match.group(1)
        if name in params:
            return str(params[name])
        if on_missing is not None:
            on_missing(name)
        return matched

    return _TOKEN.sub(replace, template)


def placeholders(template: str) -> frozenset[str]:
    """Return the placeholder names used in a template."""
    return frozenset(name for name in _TOKEN.findall(template) if name)
