from __future__ import annotations

import pickle

import pytest
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, TypeAdapter, ValidationError

from fastapi_locale import (
    LazyText,
    Localization,
    dgettext_lazy,
    dngettext_lazy,
    dnpgettext_lazy,
    dpgettext_lazy,
    gettext_lazy,
    ngettext_lazy,
    npgettext_lazy,
    pgettext_lazy,
    use_locale,
)


@pytest.fixture(autouse=True)
def _default(localization: Localization) -> None:
    localization.make_default()


def test_renders_in_the_active_locale() -> None:
    text = gettext_lazy("Hello {name}", name="Ana")
    assert str(text) == "Hello Ana"
    with use_locale("de"):
        assert str(text) == "Hallo Ana"
        assert f"[{text:>10}]" == "[ Hallo Ana]"


def test_variants() -> None:
    with use_locale("de"):
        assert str(ngettext_lazy("{n} file", "{n} files", 3)) == "3 Dateien"
        assert str(pgettext_lazy("month", "May")) == "Mai"
        assert str(npgettext_lazy("month", "May", "Mays", 1)) == "May"
        assert str(LazyText("Dashboard", domain="admin")) == "Uebersicht"
        assert str(dgettext_lazy("admin", "Dashboard")) == "Uebersicht"
        assert str(dngettext_lazy("messages", "{n} file", "{n} files", 3)) == "3 Dateien"
        assert str(dpgettext_lazy("messages", "month", "May")) == "Mai"
        assert str(dnpgettext_lazy("messages", "verb", "May", "Mays", 2)) == "Mays"


def test_equality_and_hash_do_not_depend_on_locale() -> None:
    a = gettext_lazy("Hello {name}", name="Ana")
    b = gettext_lazy("Hello {name}", name="Ana")
    c = gettext_lazy("Hello {name}", name="Raj")
    assert a == b
    assert hash(a) == hash(b)
    assert a != c
    assert hash(a) == hash(c)
    assert a != "Hello Ana"
    assert gettext_lazy("x", items=[1]) == gettext_lazy("x", items=[1])
    assert hash(gettext_lazy("x", items=[1]))


def test_repr_and_message() -> None:
    text = gettext_lazy("Hello")
    assert repr(text) == "LazyText('Hello')"
    assert text.message == "Hello"


def test_pickle_round_trip() -> None:
    text = npgettext_lazy("month", "May", "Mays", 2, extra="x")
    assert pickle.loads(pickle.dumps(text)) == text  # noqa: S301 - our own data


def test_jsonable_encoder_renders() -> None:
    with use_locale("de"):
        assert jsonable_encoder({"a": [gettext_lazy("Hello")]}) == {"a": ["Hallo"]}


class Model(BaseModel):
    text: LazyText


def test_pydantic_field() -> None:
    lazy = gettext_lazy("Hello")
    model = Model(text=lazy)
    assert model.text is lazy
    assert Model(text="plain").text == "plain"
    assert model.model_dump()["text"] is lazy
    with use_locale("de"):
        assert model.model_dump_json() == '{"text":"Hallo"}'
    with pytest.raises(ValidationError):
        Model(text=1)


def test_json_schema_is_a_string() -> None:
    assert TypeAdapter(LazyText).json_schema() == {"type": "string"}
    assert Model.model_json_schema()["properties"]["text"] == {"title": "Text", "type": "string"}


def test_any_positions_render_in_json_mode() -> None:
    adapter = TypeAdapter(dict[str, object])
    lazy = gettext_lazy("Hello")
    with use_locale("de"):
        assert adapter.dump_json({"a": lazy}) == b'{"a":"Hallo"}'
    assert adapter.dump_python({"a": lazy})["a"] is lazy
