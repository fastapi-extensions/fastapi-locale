# Configuration

Everything is configured with one `LocaleConfig`, passed to `Localization`:

```python
from pathlib import Path

from fastapi_locale import LocaleConfig, Localization

i18n = Localization(
    LocaleConfig(
        default_locale="en",
        supported_locales=["en", "de", "hi", "pt-BR"],
        catalog_dirs=[Path(__file__).parent / "locales"],
    )
)
```

## Options

| Option | Default | Meaning |
| --- | --- | --- |
| `default_locale` | required | Used when no source matches. Must be one of `supported_locales`. |
| `supported_locales` | required | Every locale the application serves. A request never gets a locale outside this list. |
| `catalog_dirs` | `()` | Directories laid out as `<dir>/<locale>/LC_MESSAGES/<domain>.mo`. Later directories override earlier ones. |
| `default_domain` | `"messages"` | Domain used by `gettext()` and the other functions without a `d` prefix. |
| `source_locale` | `"en"` | The language your msgids are written in. It needs no catalog. |
| `sources` | query `lang`, then `Accept-Language` | Where the locale comes from, in order. See [choosing the locale](locale-resolution.md). |
| `builtin_catalogs` | `True` | Load the library's own translations: the validation error messages and FastAPI's schema text. |
| `localize_openapi` | `True` | Serve the OpenAPI schema in the request's locale. See [API documentation](api-documentation.md). |

Tags are normalized, so `pt_BR`, `pt-br` and `pt-BR` all mean `pt-BR`. Invalid values raise
`ConfigurationError` with the name of the option. List options take a list even for one entry:
`catalog_dirs=["locales"]`, not `catalog_dirs="locales"`.

`LocaleConfig` only checks the values. The catalog directories are read when the `Localization` is
created, and a directory that does not exist raises `CatalogLoadError` there.

## Catalog layout

```text
locales/
    messages.pot                 template written by `fastapi-locale extract`
    de/LC_MESSAGES/messages.po   German source, edited by translators
    de/LC_MESSAGES/messages.mo   compiled by `fastapi-locale compile`
    pt_BR/LC_MESSAGES/messages.po
```

Directory names may use `_` or `-`. Commit the `.po` files; `.mo` files are build output.

## Fallback

A message missing in `pt-BR` is looked up in `pt`, then in the default locale's catalog, and finally the
msgid itself is returned. A missing translation never causes an error.

A locale in the source language is the exception: it never falls back to the default locale. With
`default_locale="de"` and `source_locale="en"`, a request for `en` or `en-GB` gets the msgids, not the
German text.

## Outside requests

Code that runs outside a request (startup code, scripts, background workers) uses the default locale of
the `Localization` that was installed last. Call `i18n.make_default()` to choose another one, or use
[`use_locale()`](translating.md#another-locale-for-a-block) for a block of code.

`install()` also stores the localization on the application as `app.state.localization`.
