# fastapi-locale

[![PyPI](https://img.shields.io/pypi/v/fastapi-locale?include_prereleases)](https://pypi.org/project/fastapi-locale/)
[![Python](https://img.shields.io/pypi/pyversions/fastapi-locale)](https://pypi.org/project/fastapi-locale/)
[![CI](https://github.com/fastapi-extensions/fastapi-locale/actions/workflows/ci.yml/badge.svg)](https://github.com/fastapi-extensions/fastapi-locale/actions/workflows/ci.yml)
[![Docs](https://readthedocs.org/projects/fastapi-locale/badge/?version=latest)](https://fastapi-locale.readthedocs.io)
[![License](https://img.shields.io/pypi/l/fastapi-locale)](https://github.com/fastapi-extensions/fastapi-locale/blob/main/LICENSE)

Internationalization for [FastAPI](https://fastapi.tiangolo.com), built on standard gettext catalogs.

**Documentation:** <https://fastapi-locale.readthedocs.io>

- Picks a locale for every request from a query parameter, `Accept-Language` or a cookie, with RFC 4647
  matching and correct `Content-Language` and `Vary` headers.
- Returns FastAPI's 422 validation errors in the client's language, with correct plural forms.
- Lazy text that works in Pydantic models, response models and `HTTPException.detail`.
- Dependency injection first: `LocaleDep` and `TranslatorDep`, replaceable in tests.
- Lets a dependency switch to the signed-in user's saved language for the rest of the request.
- A command line tool to extract, update, compile and check catalogs in CI.

> **Status:** release candidate. Install it with `pip install --pre fastapi-locale`. The engineering
> documents (requirements, models, architecture, decisions) are in [docs/](docs/project-documents.md).

## Quick start

```python
from fastapi import FastAPI, HTTPException

from fastapi_locale import LocaleConfig, Localization, TranslatorDep, gettext_lazy

i18n = Localization(
    LocaleConfig(default_locale="en", supported_locales=["en", "hi", "de"], catalog_dirs=["locales"])
)
app = FastAPI()
i18n.install(app)

NOT_FOUND = gettext_lazy("Item not found")


@app.get("/items/{item_id}")
def read_item(item_id: int, tr: TranslatorDep) -> dict[str, str]:
    if item_id != 1:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return {"name": tr.gettext("Sample item")}
```

A request with `Accept-Language: de` now gets German text, German validation errors and
`Content-Language: de`.

## Translation workflow

```sh
fastapi-locale extract          # scan the code, write locales/messages.pot
fastapi-locale init --locale hi # start a new language
fastapi-locale update           # merge new messages into every .po file
fastapi-locale compile          # build .mo files
fastapi-locale check            # fail CI when catalogs are stale or broken
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The engineering documents (requirements, models, architecture,
decisions and test plan) are in [docs/](docs/project-documents.md).

## License

MIT
