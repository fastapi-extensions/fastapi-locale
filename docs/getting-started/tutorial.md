# Tutorial: a multilingual inventory API

This tutorial builds a small inventory API in German, Hindi and English. Each step adds one feature. The
finished application is in the repository as
[`examples/basic`](https://github.com/fastapi-extensions/fastapi-locale/tree/main/examples/basic).

## Step 1: set up the localization

```python title="app.py"
from pathlib import Path

from fastapi import FastAPI

from fastapi_locale import LocaleConfig, Localization, gettext_noop

i18n = Localization(
    LocaleConfig(
        default_locale="en",
        supported_locales=["en", "de", "hi"],
        catalog_dirs=[Path(__file__).parent / "locales"],
    )
)
app = FastAPI(
    title=gettext_noop("Inventory"),
    description=gettext_noop(
        "A small inventory API that answers in your language."
    ),
)
i18n.install(app)
```

`Localization` loads every catalog at once, so a broken file stops the application from starting.
`install()` adds the middleware and the error handlers. `gettext_noop()` returns its text unchanged; it
only marks the title and description so the extractor finds them. The
[API documentation](../guide/api-documentation.md) is translated from the catalog later.

## Step 2: translate responses

```python
from fastapi_locale import LocaleDep, TranslatorDep


@app.get("/")
async def welcome(tr: TranslatorDep, locale: LocaleDep) -> dict[str, str]:
    return {
        "message": tr.gettext("Welcome to the inventory"),
        "locale": locale.tag,
    }
```

`TranslatorDep` is the translator for the request's locale. `LocaleDep` is the locale itself.

## Step 3: text defined once, translated per request

Some text is defined at import time, long before any request exists. Use lazy text for it:

```python
from fastapi import HTTPException
from pydantic import BaseModel, Field

from fastapi_locale import LazyText, gettext_lazy

ITEM_NOT_FOUND = gettext_lazy("Item not found")
ITEMS: dict[int, str] = {1: "Coffee", 2: "Tea"}


class Item(BaseModel):
    id: int
    name: str
    status: LazyText = gettext_lazy("In stock")
    summary: str = ""


@app.get("/items/{item_id}", summary=gettext_noop("Read an item"))
async def read_item(item_id: int) -> Item:
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail=ITEM_NOT_FOUND)
    return Item(id=item_id, name=ITEMS[item_id])
```

`status` and `detail` are translated when the response is written, in the locale of that response.
Fields that hold lazy text are typed `LazyText`, not `str`.

## Step 4: plurals and validation

```python
class NewItem(BaseModel):
    name: str = Field(
        min_length=3, description=gettext_noop("Display name of the item")
    )
    quantity: int = Field(gt=0)


@app.post("/items", status_code=201)
async def create_item(item: NewItem, tr: TranslatorDep) -> Item:
    item_id = max(ITEMS) + 1
    ITEMS[item_id] = item.name
    summary = tr.ngettext(
        "{n} unit of {name} added",
        "{n} units of {name} added",
        item.quantity,
        name=item.name,
    )
    return Item(id=item_id, name=item.name, summary=summary)
```

`ngettext` picks the right form for the number, following each language's rules. Invalid input, such as a
two-letter name or a quantity of zero, now returns a 422 in the client's language with no further code.

## Step 5: the user's saved language

Real applications load the user in a dependency. Apply the user's language there:

```python
from contextlib import suppress
from typing import Annotated

from fastapi import Depends, Header

from fastapi_locale import UnsupportedLocaleError, set_locale


async def current_user(
    x_user_language: Annotated[str | None, Header()] = None,
) -> None:
    """Stand-in for real authentication: apply the user's saved language."""
    if x_user_language:
        with suppress(UnsupportedLocaleError):
            set_locale(x_user_language)
```

Add `dependencies=[Depends(current_user)]` to `create_item`. A request with `X-User-Language: hi` now
gets Hindi text, Hindi validation errors and `Content-Language: hi`, even if the browser asks for German.

## Step 6: catalogs

Configure the command line tool in `pyproject.toml`:

```toml
[tool.fastapi-locale]
sources = ["."]
catalog_dir = "locales"
```

Extract the messages and start the two languages:

```sh
fastapi-locale extract
fastapi-locale init --locale de
fastapi-locale init --locale hi
```

Translate `locales/de/LC_MESSAGES/messages.po` and `locales/hi/LC_MESSAGES/messages.po`. A plural entry has
one `msgstr` per plural form of the language:

```po
#, python-brace-format
msgid "{n} unit of {name} added"
msgid_plural "{n} units of {name} added"
msgstr[0] "{n} Einheit {name} hinzugefügt"
msgstr[1] "{n} Einheiten {name} hinzugefügt"
```

Check and compile:

```sh
fastapi-locale check --require-complete
fastapi-locale compile
```

## Step 7: try it

```sh
uvicorn app:app --reload
curl -s -H "Accept-Language: de" http://127.0.0.1:8000/
curl -s -H "Accept-Language: hi" http://127.0.0.1:8000/items/9
curl -s -H "X-User-Language: hi" -H "Content-Type: application/json" \
     -d '{"name": "Milk", "quantity": 3}' http://127.0.0.1:8000/items
```

Open `http://127.0.0.1:8000/docs` in a browser set to German: the title, summaries, field descriptions
and response texts are German too.

## Step 8: test it

```python
from fastapi.testclient import TestClient

from app import app, i18n

client = TestClient(app)


def test_welcome_in_hindi() -> None:
    with i18n.override("hi"):
        assert client.get("/").json()["locale"] == "hi"


def test_validation_errors_in_german() -> None:
    response = client.post(
        "/items",
        json={"name": "ab", "quantity": 0},
        headers={"Accept-Language": "de"},
    )
    messages = [error["msg"] for error in response.json()["detail"]]
    assert "Eingabe muss größer als 0 sein" in messages
```

See [testing](../guide/testing.md) for the other helpers.
