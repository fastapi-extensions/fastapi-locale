# Validation errors

`install()` replaces FastAPI's 422 handler with one that returns the same response, with each `msg` in
the request's locale:

```json
{
  "detail": [
    {
      "type": "greater_than",
      "loc": ["body", "price"],
      "msg": "Eingabe muss größer als 0 sein",
      "input": 0,
      "ctx": {"gt": 0}
    }
  ]
}
```

Only `msg` changes. Clients that key on `type` keep working.

A message is replaced only when a translation exists for it. In the source language, and in a language
with no translation, the response is exactly what FastAPI returns without the library.

## Built-in languages

The library ships translations of all Pydantic error messages for German, Spanish, French, Hindi and
Portuguese (Brazil). The Brazilian catalog also serves `pt` and `pt-PT` until a catalog for those exists.
Other languages fall back to English. Contributions of new languages are welcome; see the contributing
guide.

## Overriding a message

Add a `fastapi_locale.po` catalog next to your own, for example `locales/de/LC_MESSAGES/fastapi_locale.po`.
Its entries take priority over the built-in ones. Use the error type as the message context:

```po
msgid ""
msgstr ""
"Content-Type: text/plain; charset=utf-8\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\n"

msgctxt "greater_than"
msgid "Input should be greater than {gt}"
msgstr "Bitte einen Wert über {gt} eingeben"
```

`fastapi-locale compile` builds it with your other catalogs, and `fastapi-locale check` validates it.
The English templates are in `fastapi_locale/locales/fastapi_locale.pot` inside the installed package.

## Your own validators

Validators run inside the request, so translate the message when you raise it:

```python
@field_validator("code")
@classmethod
def check_code(cls, value: str) -> str:
    if not value.isalnum():
        raise ValueError(gettext("Use only letters and digits"))
    return value
```

The response shows the translated prefix and your message, for example
`Wertfehler, Nur Buchstaben und Ziffern verwenden`.

## Your own handler

If you register your own `RequestValidationError` handler before calling `install()`, it is kept. Call
`localize_errors(exc)` inside it to get the translated errors.

The same holds for `HTTPException`. Your own handler must render lazy text in `detail` itself; passing
the detail through `jsonable_encoder()` does that.

## Mounted applications

Exception handlers belong to one FastAPI application. Call `install()` on each mounted FastAPI application
too:

```python
i18n.install(app)
i18n.install(admin_app)
app.mount("/admin", admin_app)
```

The locale is still resolved once per request, and `set_locale()` in either application changes it for
both.

## Known limits

- Some Pydantic context values are already English text, for example the parser detail in `date_parsing`
  or the list in `literal_error` (`'a' or 'b'`). Those parts stay in English.
- Starlette's own error texts, such as `Not Found` for an unknown path, are not translated. Raise an
  `HTTPException` with lazy text, or register a handler for the status code, where that matters.
- Validation errors of a WebSocket route are sent by FastAPI as the close reason and are not translated.

## Handlers for unhandled errors

A handler registered for `Exception` runs after the request's locale scope has closed, so `gettext()`
there uses the default locale. Use the locale stored on the request:

```python
@app.exception_handler(Exception)
async def on_error(request: Request, exc: Exception) -> JSONResponse:
    with use_locale(request.state.locale.locale):
        detail = gettext("Something went wrong")
    return JSONResponse({"detail": detail}, status_code=500)
```

Starlette sends this response outside the locale middleware, so it carries no `Content-Language` header
unless the handler sets one.
