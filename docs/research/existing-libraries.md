# Existing libraries

| Field | Value |
| --- | --- |
| Document | Survey of existing i18n libraries for FastAPI and Starlette |
| Version | 1.0 |
| Status | Approved |
| Owner | Kapil Dagur |
| Last updated | 2026-09-28 |

## 1. Purpose

Before starting a new library I wanted to know whether the problem is already solved. This document
records what the existing packages do, where they fall short for FastAPI users, and what that means for
the [requirements](../requirements/software-requirements-specification.md).

## 2. Method

I read the source of each package below (latest release on PyPI as of 2026-09-26) instead of relying on
READMEs, and ran small experiments against FastAPI 0.141.1, Pydantic 2.13.5 (pydantic-core 2.46.5), Babel 2.18.0
and Starlette 1.7.0 on Python 3.12.

## 3. Summary

| Package | Version, released | Size | Locale state | Resolution | Lazy strings | Pydantic / 422 | OpenAPI |
| --- | --- | --- | --- | --- | --- | --- | --- |
| starlette-babel | 1.2.0, Jul 2026 | ~1.5k LOC | ContextVar, pure ASGI | query, cookie, `scope["user"]`, Accept-Language | Babel `LazyProxy` | No | No |
| starlette-i18n | 3.0.0, Jul 2026 | ~330 LOC | ContextVar, pure ASGI, token reset | cookie, Accept-Language (RFC 4647 lookup) | Babel `LazyProxy` | No | No |
| fastapi-babel | 1.0.0, Dec 2024 | ~570 LOC | ContextVar, `BaseHTTPMiddleware`, never reset | custom selector or Accept-Language | `LazyText` (not a str) | No | No |
| fastapi-i18n | 0.12.0, Nov 2025 | ~100 LOC | ContextVar set in a yield dependency | first Accept-Language entry only | None | No | No |
| asgi-babel | 0.11.0, Nov 2025 | ~200 LOC | ContextVar, asgi-tools middleware | selector, default Accept-Language | None | No | No |
| pydantic-i18n | 0.4.5, Sep 2024 | ~240 LOC | none (caller passes locale) | none | n/a | Yes, by English text | No |

pydantic-i18n is the only package that translates validation errors, so it gets a closer look in section 5.

## 4. Notes per package

**starlette-babel.** The most complete of the group. It has pluggable locale selectors, gettext / ngettext /
pgettext / npgettext and their lazy variants, multiple domains, Babel formatters for dates, numbers and
currency, timezone middleware and Jinja helpers. Gaps for FastAPI users:

- It sends `Content-Language` but not `Vary: Accept-Language`, so shared caches can serve the wrong language.
- `LocaleFromUser` reads `scope["user"]`, which only Starlette's `AuthenticationMiddleware` fills in. Most
  FastAPI apps load the user in a dependency, so this selector never sees it.

- The ContextVar default is hardcoded to `en_US`, not the configured `default_locale`, so code running
  outside a request (workers, scripts) gets `en_US`.

- `switch_locale` restores the old value with `set` instead of a `Token`.
- Its `LazyString` is a Babel `LazyProxy`, which breaks in FastAPI (see section 6).

**starlette-i18n.** Small and careful. Pure ASGI middleware, resets the ContextVar with a token, correct
RFC 9110 q-value parsing, RFC 4647 lookup, and it sends both `Content-Language` and `Vary`. Its scope is
narrow: one domain, no pgettext, no query or path selector, no user hook, and `gettext_lazy` is also a
Babel `LazyProxy`. Good code to learn from, but not a base for what we need.

**fastapi-babel.** The best-known name, with no release in almost two years. Problems:

- It uses `BaseHTTPMiddleware`.
- The `gettext` property calls `translation(...).install()` on each access. That rebinds `builtins._` for
  the whole process on each request, so concurrent requests can race.

- The ContextVar is set but never reset.
- Accept-Language matching only understands `xx` or `xx-XX` tags, and it sorts q-values as strings.
- `LazyText` is a plain object that translates in `__repr__`, so it cannot be used as a string or serialized.

**fastapi-i18n.** Sets the locale in an app-level yield dependency. It uses only the first
Accept-Language entry and ignores q-values. As section 6 shows, a locale set in a dependency is not visible in
the validation error handler.

**asgi-babel.** Generic ASGI, built on asgi-tools. It keeps a module-level global for the middleware
instance, sets the ContextVar without resetting it, and caches catalogs by language only, so `pt_BR` and
`pt_PT` would share one. Nothing FastAPI-specific.

## 5. pydantic-i18n in detail

It is the only direct overlap with our main feature. How it works: it builds one big regex from all English
message templates, with each `{placeholder}` turned into `(.+)`. It matches the rendered English `msg`
against that regex, puts the captured values back as positional `{}` and looks up the translation. It can
also fall back to looking up by error `type`. For FastAPI, the README gives a recipe (a dependency plus an
exception handler) rather than shipping one.

Weak points:

- It keys on English text, not on the stable error `type` and `ctx`. Pydantic changes message wording
  between releases, and translations then silently stop matching.

- Placeholders are positional and come from regex capture, so a translation cannot reorder them or use
  them by name, and greedy `(.+)` can capture the wrong span.

- It gets plurals wrong. Pydantic renders plurals in English inside `ctx` (for example
  `string_too_short` uses `{expected_plural}`), so it does not use the target language's plural rules.

- It raises `ValueError` for an unknown locale. There is no fallback chain.
- There's no release since September 2024.

So a validation error catalog is not new, but none of these packages builds one on error `type` and `ctx`
with gettext plural rules, request locale and a ready-made FastAPI handler.

## 6. Experiments

Each result below comes from a small script run against the versions listed in section 2.

**Babel `LazyProxy` (used by starlette-babel and starlette-i18n) fails in every FastAPI path I tried:**

| Use | Result |
| --- | --- |
| `HTTPException(detail=lazy)` with the default handler | `TypeError: Object of type LazyProxy is not JSON serializable` |
| Returned into a `str` field of a `response_model` | `ResponseValidationError: Input should be a valid string` |
| `Model(msg=lazy)` | `ValidationError: Input should be a valid string` |
| Returned inside a plain dict | `ValueError` from `jsonable_encoder` |
| `summary=` / `Field(description=)` then `app.openapi()` | `TypeError: unhashable type: 'LazyProxy'` |

**Two lazy string designs, tried as prototypes:**

- A `str` subclass that overrides `__str__` looks right in f-strings but is not lazy where it matters:
  `json.dumps` writes the raw msgid, not the translation. Rejected.

- A plain class with `__get_pydantic_core_schema__` (plain serializer calling `str`) serializes correctly
  in fields typed as the lazy type, and works through `jsonable_encoder` once registered in
  `fastapi.encoders.ENCODERS_BY_TYPE`. It still fails when put in a `str`-typed field, and with the default
  `HTTPException` handler, which calls `json.dumps` directly. So we need to ship our own `HTTPException`
  handler, and document that model fields holding lazy text use our type, not `str`.

**Where the locale ContextVar is visible:**

| Set in | Sync dependency | Endpoint | 422 handler | Background task |
| --- | --- | --- | --- | --- |
| Pure ASGI middleware | yes | yes | yes | yes |
| App-level yield dependency | yes | yes | **no** | not tested |

A locale that only a dependency sets is missing when `RequestValidationError` is handled. Localized 422s
therefore need the locale resolved in middleware (or resolved again inside the handler).

**Pydantic error catalog size.** pydantic-core 2.46.5 lists 104 error types. 47 of them have `ctx`
placeholders. Some templates carry English plural logic in `ctx` (`{expected_plural}`), so our catalog should
use ngettext on the numeric value (`min_length`, `max_length` and so on) and ignore those English-only keys.

## 7. Conclusions

1. The gap is real, but narrower than it first looked. Locale resolution and gettext wrappers are
   solved well enough (starlette-i18n, starlette-babel). The FastAPI-specific parts are not solved anywhere:
   - localized 422s keyed on error `type` and `ctx`, with proper plurals
   - a lazy string type that works with Pydantic, `jsonable_encoder`, `HTTPException` and OpenAPI
   - a DI-first API
   - user-preference locale coming from a FastAPI dependency
   - localized OpenAPI
2. Build our own resolution layer instead of depending on starlette-babel. We need pure ASGI middleware,
   token reset, `Vary`, and a default locale taken from config. starlette-babel's selector signature
   (`HTTPConnection -> str | None`) is a good shape to copy.
3. Middleware owns resolution; dependencies are how code reads it. A dependency such as `LocaleDep` reads the
   ContextVar that the middleware set.
4. A user's saved language is usually loaded in an auth dependency, which runs
   after the middleware. Options are to let a dependency override the locale for the rest of the request
   (knowing the 422 handler will not see it), or to let the 422 handler call a user-supplied async hook.
   This is open issue OI-05 in the requirements.
5. Lazy strings: a non-str class with Pydantic core schema support, registered with `jsonable_encoder`,
   plus our own `HTTPException` handler. OpenAPI needs its own pass that resolves lazy text per locale,
   because FastAPI hashes and caches the schema. This will be decided in an ADR.
