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
from fastapi_locale import AcceptLanguageSource, CookieSource, LocaleConfig, QueryParamSource

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

Load the user in a dependency, as usual, and call `set_locale()`:

```python
from fastapi_locale import UnsupportedLocaleError, set_locale


async def current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    user = await users.get_by_token(token)
    try:
        set_locale(user.language)
    except UnsupportedLocaleError:
        pass
    return user
```

The rest of the request uses the new locale: route code, lazy text, validation errors and the
`Content-Language` header. FastAPI runs dependencies before it validates the request body, so the user's
language applies to body validation errors too. If validation fails in the dependency's own parameters,
the dependency does not run and the request keeps the locale from the request.

## Caching

Responses carry `Vary` with every header the sources read (`Accept-Language`, `Cookie`), so shared caches
store one copy per language. The query parameter needs no entry because the URL is already part of the
cache key.
