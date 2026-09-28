# fastapi-locale

**Internationalization for FastAPI, built on standard gettext catalogs.**

fastapi-locale picks a language for every request, translates your messages with `.po` files that any
translation tool understands, and returns FastAPI's validation errors and API documentation in the
client's language.

```python
from fastapi import FastAPI
from fastapi_locale import LocaleConfig, Localization

i18n = Localization(
    LocaleConfig(default_locale="en", supported_locales=["en", "de", "hi"])
)
app = FastAPI()
i18n.install(app)
```

With nothing more than this, a German client already gets German validation errors:

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

## Features

| Feature | What it does |
| --- | --- |
| **Per-request locale** | From a query parameter, cookie or `Accept-Language`, matched with RFC 4647 and announced with `Content-Language` and `Vary`. |
| **Localized validation errors** | Every Pydantic error type, with plural forms that follow each language. The response shape stays exactly FastAPI's. |
| **Localized API docs** | Swagger UI and ReDoc follow the browser's language. |
| **Lazy text** | Translatable text in Pydantic models, response models and `HTTPException.detail`. |
| **Dependency injection** | `LocaleDep` and `TranslatorDep`, replaceable in tests. |
| **The user's saved language** | Call `set_locale()` in your auth dependency; the whole request follows, errors included. |
| **Standard catalogs** | GNU gettext `.po` files, CLDR plural rules, and a CLI that checks catalogs in CI. |
| **Built for production** | Async-safe, no I/O per request, fully typed, tested on Python 3.11 to 3.14. |

Built-in translations of the error messages: German, Spanish, French, Hindi and Portuguese (Brazil).

## Where to go next

- New here? Start with the [quick start](getting-started/quickstart.md), then the
  [tutorial](getting-started/tutorial.md).
- Looking for a specific task? Browse the [user guide](guide/configuration.md).
- Moving from another library? See [migrating](guide/migration.md).
- Need exact signatures? See the [API reference](reference/setup.md).
