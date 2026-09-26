"""Accept-Language parsing as defined by RFC 9110, section 12.5.4."""

from __future__ import annotations

import re

__all__ = ["DEFAULT_MAX_LENGTH", "parse_accept_language"]

DEFAULT_MAX_LENGTH = 1024

# RFC 9110, section 12.4.2: qvalue = ( "0" [ "." 0*3DIGIT ] ) / ( "1" [ "." 0*3("0") ] )
_QVALUE = re.compile(r"0(?:\.[0-9]{0,3})?|1(?:\.0{0,3})?")


def parse_accept_language(header: str, max_length: int = DEFAULT_MAX_LENGTH) -> list[str]:
    """Return the acceptable language ranges of a header value, most preferred first.

    Malformed members, the ``*`` wildcard and refused ranges (``q=0``) are left out. Input longer
    than ``max_length`` is cut at the last complete member so parsing cost stays bounded.
    """
    if len(header) > max_length:
        cut = header.rfind(",", 0, max_length)
        header = header[:cut] if cut > 0 else ""

    ranges: list[tuple[float, int, str]] = []
    for position, member in enumerate(header.split(",")):
        language_range, _, parameters = member.partition(";")
        language_range = language_range.strip()
        if not language_range or language_range == "*":
            continue
        weight = _weight(parameters)
        if weight is not None and weight > 0:
            ranges.append((weight, position, language_range))

    ranges.sort(key=lambda item: (-item[0], item[1]))
    return [language_range for _, _, language_range in ranges]


def _weight(parameters: str) -> float | None:
    """Return the q value of a member, 1.0 when absent, or ``None`` when it is malformed."""
    if not parameters:
        return 1.0
    weight = 1.0
    for parameter in parameters.split(";"):
        name, separator, value = parameter.strip().partition("=")
        if name.strip().lower() != "q":
            continue
        value = value.strip()
        if not separator or not _QVALUE.fullmatch(value):
            return None
        weight = float(value)
    return weight
