# Choosing the locale

## Sources

By default the locale comes from, in order:

1. the `lang` query parameter,
2. the `Accept-Language` header, honouring q-values.

The first value that matches a supported locale wins. If nothing matches, the default locale is used.

Choose your own sources and order:

```python
from fastapi_locale import (
    AcceptLanguageSource,
    CookieSource,
    LocaleConfig,
    QueryParamSource,
)

LocaleConfig(
    default_locale="en",
    supported_locales=["en", "de"],
    sources=[
        QueryParamSource("hl"),
        CookieSource("lang"),
        AcceptLanguageSource(),
    ],
)
```

`CookieSource` reads a cookie your application sets, by default one named `locale`. It is not among the
default sources because it adds `Cookie` to the `Vary` header of every response; see [caching](#caching).

## Matching

A value from a source is matched against `supported_locales` in two steps:

1. RFC 4647 lookup: the value itself, then shorter and shorter prefixes. `hi-IN` uses `hi` when only `hi`
   is supported.
2. If that finds nothing, the first supported locale in the same language. `pt` and `pt-PT` use `pt-BR`
   when that is the only Portuguese locale. A different script is never crossed: `zh-Hant-TW` does not
   use `zh-Hans`.

Values that are not valid language tags are skipped.

## Your own source

A source is any callable that takes the connection and returns a tag, a list of tags, or `None`:

```python
def from_subdomain(conn: HTTPConnection) -> str | None:
    return conn.url.hostname.split(".")[0] if conn.url.hostname else None
```

Sources must be fast and must not do I/O. A source never breaks a request: one that raises is logged and
skipped, and values that are not language tags are ignored.

A source that reads a request header should say so, or shared caches may serve one language to everyone.
Give it a `vary` attribute, and optionally a `name` for logs:

```python
class HeaderSource:
    name = "x-language"
    vary = ("X-Language",)

    def __call__(self, conn: HTTPConnection) -> str | None:
        return conn.headers.get("x-language")
```

## What the request ended up with

`request.state.locale` is a [`RequestLocale`](../reference/context.md#fastapi_locale.RequestLocale). Its
`locale` is the locale in use, and `decided_by` names what chose it: a source (`query`, `cookie`,
`accept-language`, or your source's name), `default`, `set_locale`, or `override` in tests.

## The user's saved language

A signed-in user's own choice usually beats the browser's. See [the user's saved language](user-language.md).

## Your own middleware

`install()` adds the locale middleware. Middleware you add before calling `install()` runs inside it and
sees the request's locale. Middleware you add afterwards runs outside it: `get_locale()` there returns the
default locale, although `request.state.locale` is available once the inner application has run.

## Caching

See also [deployment](deployment.md).

Responses carry `Vary` with every header the sources read, so shared caches store one copy per language.
With the default sources that is `Accept-Language`. The query parameter needs no entry because the URL is
already part of the cache key.
