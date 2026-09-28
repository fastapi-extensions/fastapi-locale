# Migrating from other libraries

All of these libraries use gettext catalogs, so your `.po` files keep working. Point `catalog_dirs` at
the same directory.

## From fastapi-babel

| fastapi-babel | fastapi-locale |
| --- | --- |
| `BabelConfigs(ROOT_DIR=..., BABEL_DEFAULT_LOCALE="en", BABEL_TRANSLATION_DIRECTORY="lang")` | `LocaleConfig(default_locale="en", supported_locales=[...], catalog_dirs=["lang"])` |
| `Babel(configs=...)` and `app.add_middleware(BabelMiddleware, babel_configs=...)` | `Localization(config).install(app)` |
| `from fastapi_babel import _` | `from fastapi_locale import gettext as _` |
| `lazy_gettext("...")` | `gettext_lazy("...")` |
| `locale_selector=` | `LocaleConfig(sources=[...])` |
| `babel.run_cli()` and `pybabel` commands | `fastapi-locale extract / init / update / compile` |

Differences to expect:

- The list of supported locales is explicit. A request can no longer select any directory that happens to
  exist.
- `Accept-Language` q-values are honoured.
- Translations are request-safe; fastapi-babel installs `_` into Python's builtins on every request.
- Validation errors and the API documentation are translated too.

## From starlette-babel

| starlette-babel | fastapi-locale |
| --- | --- |
| `Middleware(LocaleMiddleware, locales=[...], default_locale="en")` | `Localization(LocaleConfig(...)).install(app)` |
| `load_messages_from_directories([...])` | `LocaleConfig(catalog_dirs=[...])` |
| `LocaleFromQuery()`, `LocaleFromCookie()`, `LocaleFromHeader(...)` in `selectors=` | `QueryParamSource()`, `CookieSource()`, `AcceptLanguageSource()` in `sources=` |
| `LocaleFromUser()` | `set_locale(user.language)` in your auth dependency |
| `gettext_lazy`, `ngettext`, `pgettext`, `npgettext` | Same names |
| `switch_locale("de")` | `use_locale("de")` |
| `get_locale()` returns a Babel `Locale` | `get_locale()` returns a `fastapi_locale.Locale`; `locale.tag` is the string |

Differences to expect:

- Lazy text works in Pydantic models, response models and `HTTPException.detail`.
- Responses carry `Vary` as well as `Content-Language`.
- In plural messages, use `{n}` for the count, or pass your own names:
  `ngettext("{count} file", "{count} files", n, count=n)`.
- Date, number and timezone formatting are not part of fastapi-locale yet; keep using Babel's `format_*`
  functions with `get_locale().tag`.

## From starlette-i18n

Replace `LocaleMiddleware(catalog=...)` with `Localization(...).install(app)`. `gettext`, `ngettext` and
`gettext_lazy` keep their names. The cookie and `Accept-Language` sources match starlette-i18n's
defaults, with the `lang` query parameter added in front.
