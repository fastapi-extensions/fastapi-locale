# fastapi-locale

Internationalization for [FastAPI](https://fastapi.tiangolo.com), built on standard gettext catalogs.

fastapi-locale picks a language for every request and translates your messages with `.po` files that
any translation tool understands. It also returns FastAPI's validation errors in the client's language.

## What you get

- **Per-request locale** from a query parameter, cookie or `Accept-Language`, matched with RFC 4647 and
  announced with `Content-Language` and `Vary`.
- **Localized 422 errors** for every Pydantic error type, with plural forms that follow each language.
  Built-in translations: German, Spanish, French, Hindi and Portuguese (Brazil).
- **Lazy text** that works in Pydantic models, response models and `HTTPException.detail`.
- **Dependency injection**: `LocaleDep` and `TranslatorDep`, replaceable in tests.
- **The user's saved language**: call `set_locale()` in your auth dependency and the whole request
  follows it, including validation errors.
- **A command line tool** to extract, update, compile and check catalogs.

## Five lines of setup

```python
from fastapi import FastAPI
from fastapi_locale import LocaleConfig, Localization

i18n = Localization(LocaleConfig(default_locale="en", supported_locales=["en", "de", "hi"]))
app = FastAPI()
i18n.install(app)
```

Validation errors are now localized for German and Hindi clients. Continue with
[getting started](guide/getting-started.md) to translate your own messages.
