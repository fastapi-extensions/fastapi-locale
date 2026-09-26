# Getting started

## Install

```sh
uv add fastapi-locale     # or: pip install fastapi-locale
```

## Set up the application

```python
from pathlib import Path

from fastapi import FastAPI
from fastapi_locale import LocaleConfig, Localization

i18n = Localization(
    LocaleConfig(
        default_locale="en",
        supported_locales=["en", "de", "hi"],
        catalog_dirs=[Path(__file__).parent / "locales"],
    )
)
app = FastAPI()
i18n.install(app)
```

`Localization` loads every catalog when it is created, so a missing or broken file stops the application
from starting instead of failing later. `install()` adds the middleware that picks the locale of each
request and the exception handlers that localize error responses.

## Translate a message

```python
from fastapi_locale import TranslatorDep


@app.get("/")
async def welcome(tr: TranslatorDep) -> dict[str, str]:
    return {"message": tr.gettext("Welcome, {name}", name="Asha")}
```

## Create the catalogs

Tell the command line tool where things are, in `pyproject.toml`:

```toml
[tool.fastapi-locale]
sources = ["app"]
locales_dir = "app/locales"
```

Then:

```sh
fastapi-locale extract           # writes app/locales/messages.pot
fastapi-locale init --locale de  # creates app/locales/de/LC_MESSAGES/messages.po
# translate the .po file in any gettext editor (Poedit, Weblate, a text editor)
fastapi-locale compile           # builds the .mo files the application loads
```

A request with `Accept-Language: de` now gets German text and `Content-Language: de`.

## Next steps

- [Translating messages](translating.md): plurals, context, domains and lazy text
- [Choosing the locale](locale-resolution.md): sources, their order, and the user's saved language
- [Validation errors](validation-errors.md)
- [Testing](testing.md)
- [Command line tool](command-line.md)
