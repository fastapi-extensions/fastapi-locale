# fastapi-locale

Internationalization for [FastAPI](https://fastapi.tiangolo.com), built on standard gettext catalogs.

- Picks a locale for every request from a query parameter, cookie or `Accept-Language`, with RFC 4647
  matching and correct `Content-Language` and `Vary` headers.
- Returns FastAPI's 422 validation errors in the client's language, with correct plural forms.
- Lazy text that works in Pydantic models, response models and `HTTPException.detail`.
- Dependency injection first: `LocaleDep` and `TranslatorDep`, replaceable in tests.
- Lets a dependency switch to the signed-in user's saved language for the rest of the request.
- A command line tool to extract, update, compile and check catalogs in CI.

> **Status:** in development, not yet released. The design is in [docs/](docs/project-documents.md).

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
