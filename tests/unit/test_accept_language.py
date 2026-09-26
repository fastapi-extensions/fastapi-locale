from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from fastapi_locale._accept_language import parse_accept_language


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("de", ["de"]),
        ("da, en-gb;q=0.8, en;q=0.7", ["da", "en-gb", "en"]),
        ("en;q=0.5, fr", ["fr", "en"]),
        ("fr;q=0.5, de;q=0.5, en;q=0.5", ["fr", "de", "en"]),
        ("hi-IN,hi;q=0.9,en;q=0.5", ["hi-IN", "hi", "en"]),
        ("en;q=0, de", ["de"]),
        ("*, de;q=0.5", ["de"]),
        ("de;q=1.0", ["de"]),
        ("de;q=1.000", ["de"]),
        ("de;Q=0.5", ["de"]),
        ("de ; q = 0.5 ", ["de"]),
        ("de;level=1", ["de"]),
        ("", []),
        (",,,", []),
    ],
)
def test_parses_rfc_9110_examples(header: str, expected: list[str]) -> None:
    assert parse_accept_language(header) == expected


@pytest.mark.parametrize(
    "header", ["de;q=1.5", "de;q=0.1234", "de;q=abc", "de;q", "de;q=-1", "de;q=1.01"]
)
def test_malformed_weights_drop_the_member(header: str) -> None:
    assert parse_accept_language(header + ", fr") == ["fr"]


def test_long_headers_are_cut_at_a_member_boundary() -> None:
    header = "de, " + ", ".join(["xx"] * 500) + ", fr"
    result = parse_accept_language(header, max_length=20)
    assert result[0] == "de"
    assert "fr" not in result


def test_a_single_overlong_member_yields_nothing() -> None:
    assert parse_accept_language("a" * 50, max_length=10) == []


@given(st.text(max_size=300))
def test_never_raises(header: str) -> None:
    parse_accept_language(header)
