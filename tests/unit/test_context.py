from __future__ import annotations

import pytest

from fastapi_locale import (
    Localization,
    LocalizationNotConfiguredError,
    NoActiveRequestError,
    UnsupportedLocaleError,
    dgettext,
    dngettext,
    dnpgettext,
    dpgettext,
    get_locale,
    get_translator,
    gettext,
    gettext_noop,
    ngettext,
    npgettext,
    pgettext,
    set_locale,
    use_locale,
)
from fastapi_locale._context import (
    current_request_locale,
    enter_request,
    exit_request,
    use_default_locale,
)


def test_nothing_configured_raises() -> None:
    with pytest.raises(LocalizationNotConfiguredError, match="no localization is set up"):
        get_translator()
    with pytest.raises(LocalizationNotConfiguredError), use_locale("de"):
        pass


def test_process_default_is_used_outside_requests(localization: Localization) -> None:
    localization.make_default()
    assert get_locale().tag == "en"
    assert gettext("Hello") == "Hello"


def test_use_locale_switches_and_restores(localization: Localization) -> None:
    localization.make_default()
    with use_locale("de-AT") as locale:
        assert locale.tag == "de"
        assert gettext("Hello") == "Hallo"
        with use_locale("fr"):
            assert gettext("Hello") == "Bonjour"
        assert gettext("Hello") == "Hallo"
    assert gettext("Hello") == "Hello"


def test_use_locale_restores_after_an_error(localization: Localization) -> None:
    localization.make_default()
    with pytest.raises(RuntimeError), use_locale("de"):
        raise RuntimeError
    assert get_locale().tag == "en"


def test_use_locale_rejects_unsupported(localization: Localization) -> None:
    localization.make_default()
    with pytest.raises(UnsupportedLocaleError), use_locale("sw"):
        pass


def test_module_functions_delegate(localization: Localization) -> None:
    localization.make_default()
    with use_locale("de"):
        assert gettext("Hello {name}", name="Ana") == "Hallo Ana"
        assert ngettext("{n} file", "{n} files", 2) == "2 Dateien"
        assert pgettext("month", "May") == "Mai"
        assert npgettext("month", "May", "Mays", 1) == "May"
        assert dgettext("admin", "Dashboard") == "Uebersicht"
        assert dngettext("admin", "{n} file", "{n} files", 1) == "1 file"
        assert dpgettext("messages", "verb", "May") == "Darf"
        assert dnpgettext("messages", "verb", "May", "Mays", 3) == "Mays"
    assert gettext_noop("Hello") == "Hello"


def test_set_locale_outside_a_request_raises(localization: Localization) -> None:
    localization.make_default()
    with pytest.raises(NoActiveRequestError, match="only during a request"):
        set_locale("de")
    with use_locale("fr"), pytest.raises(NoActiveRequestError):
        set_locale("de")


def test_set_locale_changes_the_request_holder(localization: Localization) -> None:
    store = localization._store
    holder, token = enter_request(store.default_translator, "default", store)
    try:
        assert holder.decided_by == "default"
        assert set_locale("hi-IN").tag == "hi"
        assert holder.locale.tag == "hi"
        assert holder.decided_by == "set_locale"
        assert repr(holder) == "RequestLocale('hi', decided_by='set_locale')"
        with use_locale("fr"):
            assert gettext("Hello") == "Bonjour"
            set_locale("de")
            assert gettext("Hello") == "Bonjour"
            assert current_request_locale() is not holder
        assert gettext("Hello") == "Hallo"
        with pytest.raises(UnsupportedLocaleError):
            set_locale("sw")
        for missing in (None, ""):
            with pytest.raises(UnsupportedLocaleError):
                set_locale(missing)  # type: ignore[arg-type]
        assert get_locale().tag == "de"
    finally:
        exit_request(token)
    assert current_request_locale() is None


def test_use_default_locale(localization: Localization) -> None:
    with use_default_locale():  # nothing set up yet: the block simply runs
        pass
    localization.make_default()
    with use_locale("de"):
        with use_default_locale():
            assert get_locale().tag == "en"
        assert get_locale().tag == "de"
