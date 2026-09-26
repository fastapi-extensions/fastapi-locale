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

## Built-in languages

The library ships translations of all Pydantic error messages for German, Spanish, French, Hindi and
Portuguese (Brazil). Other languages fall back to English until a catalog exists. Contributions of new
languages are welcome; see the contributing guide.

## Overriding a message

Add a `fastapi_locale.po` catalog to your own catalog directory. Its entries take priority over the
built-in ones. Use the error type as the message context:

```po
msgctxt "greater_than"
msgid "Input should be greater than {gt}"
msgstr "Bitte einen Wert über {gt} eingeben"
```

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

## Known limits

Some Pydantic context values are already English text, for example the parser detail in `date_parsing`
or the list in `literal_error` (`'a' or 'b'`). Those parts stay in English.
