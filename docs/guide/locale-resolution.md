# Choosing the locale

## Sources

By default the locale comes from, in order:

1. the `lang` query parameter,
2. the `locale` cookie,
3. the `Accept-Language` header, honouring q-values.

The first value that matches a supported locale wins. Matching follows RFC 4647: a request for `hi-IN`
uses `hi` when only `hi` is supported. If nothing matches, the default locale is used.

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
    sources=[CookieSource("lang"), AcceptLanguageSource()],
)
```

A source can also be a plain function that returns a tag, a list of tags, or `None`:

```python
def from_subdomain(conn: HTTPConnection) -> str | None:
    return conn.url.hostname.split(".")[0] if conn.url.hostname else None
```

Sources must be fast and must not do I/O. A source that raises is logged and skipped.

## The user's saved language

A signed-in user's own choice usually beats the browser's. See [the user's saved language](user-language.md).

## Caching

See also [deployment](deployment.md).

Responses carry `Vary` with every header the sources read (`Accept-Language`, `Cookie`), so shared caches
store one copy per language. The query parameter needs no entry because the URL is already part of the
cache key.
