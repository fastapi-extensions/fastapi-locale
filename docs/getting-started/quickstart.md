# Quick start

This page takes about five minutes. You will localize validation errors, translate a message, and see
the result in German.

## 1. Localized validation errors

Create `main.py`:

```python
from fastapi import FastAPI
from pydantic import BaseModel, Field

from fastapi_locale import LocaleConfig, Localization

i18n = Localization(
    LocaleConfig(default_locale="en", supported_locales=["en", "de"])
)
app = FastAPI()
i18n.install(app)


class Item(BaseModel):
    name: str = Field(min_length=3)
    price: int = Field(gt=0)


@app.post("/items")
async def create_item(item: Item) -> Item:
    return item
```

Run it with `uvicorn main:app --reload` and send an invalid item:

```sh
curl -s -H "Accept-Language: de" -H "Content-Type: application/json" \
     -d '{"name": "ab", "price": 0}' http://127.0.0.1:8000/items
```

The `msg` of each error is in German. Everything else is exactly what FastAPI returns.

## 2. Your own messages

Add a route that translates a message:

```python
from fastapi_locale import TranslatorDep


@app.get("/")
async def welcome(tr: TranslatorDep) -> dict[str, str]:
    return {"message": tr.gettext("Welcome, {name}!", name="Asha")}
```

Tell the command line tool where your code and catalogs live, in `pyproject.toml`:

```toml
[tool.fastapi-locale]
sources = ["."]
catalog_dir = "locales"
```

Then create the German catalog:

```sh
fastapi-locale extract           # writes locales/messages.pot
fastapi-locale init --locale de  # creates locales/de/LC_MESSAGES/messages.po
```

Now that the directory exists, point the library at it:

```python
from pathlib import Path

i18n = Localization(
    LocaleConfig(
        default_locale="en",
        supported_locales=["en", "de"],
        catalog_dirs=[Path(__file__).parent / "locales"],
    )
)
```

Open `locales/de/LC_MESSAGES/messages.po` and fill in the translation:

```po
msgid "Welcome, {name}!"
msgstr "Willkommen, {name}!"
```

Compile and restart the server:

```sh
fastapi-locale compile
```

```sh
curl -s -H "Accept-Language: de" http://127.0.0.1:8000/
# {"message": "Willkommen, Asha!"}
```

## What next

The [tutorial](tutorial.md) builds a complete API step by step: lazy text, the user's saved language,
translated API docs and tests.
