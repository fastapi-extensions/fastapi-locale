# API documentation

Swagger UI (`/docs`) and ReDoc (`/redoc`) show the OpenAPI schema. fastapi-locale serves that schema in
the request's locale, so the documentation follows the reader's browser language with no extra setup.

## Mark the text

Mark titles, summaries and descriptions with `gettext_noop()`. It returns the text unchanged, so FastAPI
builds its schema as usual, and the extractor finds the text for translators:

```python
from fastapi_locale import gettext_noop

app = FastAPI(title=gettext_noop("Inventory"), description=gettext_noop("Manage your stock."))


class NewItem(BaseModel):
    name: str = Field(description=gettext_noop("Display name of the item"))


@app.get("/items/{item_id}", summary=gettext_noop("Read an item"))
async def read_item(item_id: int) -> Item: ...
```

After `fastapi-locale extract`, these texts appear in your catalogs like any other message.

## What is translated

Every `title`, `summary` and `description` in the schema: the application's title and description, tag
descriptions, operation summaries and descriptions, response descriptions, and model and field titles and
descriptions. FastAPI's own text ("Successful Response", "Validation Error" and the fields of its
validation error schema) is translated by the library's built-in catalogs.

Values under `default`, `example`, `examples`, `const` and `enum` are data and are never translated.

## Different wording for the schema

The same English text is translated the same way everywhere. When schema text needs different wording,
add a translation with the `openapi` context; it wins over the plain one:

```po
msgctxt "openapi"
msgid "Item"
msgstr "Artikel (Schema)"
```

## Docstrings

FastAPI uses a route's docstring as its description when no `description` is given. gettext tools cannot
extract docstrings, so those descriptions stay in the source language. Pass
`description=gettext_noop(...)` for text that should be translated.

## Performance

FastAPI builds the schema once. Each locale is translated on its first request and cached; a schema
with 300 routes takes about 1.5 ms to translate.

## Turning it off

```python
LocaleConfig(default_locale="en", supported_locales=["en", "de"], localize_openapi=False)
```
