# Detailed design

| Field | Value |
| --- | --- |
| Document | Detailed design |
| Version | 1.2 |
| Status | Approved |
| Owner | fastapi-locale contributors |
| Last updated | 2026-10-04 |

## 1. Purpose

This document specifies the modules, classes and public API of fastapi-locale closely enough to implement
and test them. It follows the [architecture](../architecture/software-architecture.md) and the
[ADRs](../adr/README.md). Names used here are the names used in the code.

## 2. Package layout

```text
src/fastapi_locale/
    __init__.py            public API, re-exported from the modules below
    py.typed
    config.py              LocaleConfig
    exceptions.py          exception hierarchy
    _locale.py             Locale value object, tag parsing, RFC 4647 truncation
    _accept_language.py    Accept-Language parsing
    _catalog.py            CatalogStore: loading, merging, fallback chains
    _translator.py         Translator
    _formatting.py         named placeholder substitution
    _context.py            RequestLocale, get_locale, get_translator, set_locale, use_locale
    _errors_catalog.py     ErrorTemplate table, one entry per Pydantic error type; ErrorLocalizer
    _openapi.py            translation of a generated OpenAPI schema
    sources.py             LocaleSource protocol and built-in sources
    middleware.py          LocaleMiddleware
    lazy.py                LazyText and the *_lazy functions
    handlers.py            validation and HTTP exception handlers
    openapi.py             localize_openapi: per-locale schema served by FastAPI
    dependencies.py        LocaleDep, TranslatorDep
    localization.py        Localization
    testing.py             pytest plugin: the locale marker
    cli/                   fastapi-locale command (_settings.py, _commands.py)
    locales/               built-in error catalogs as .pot and .po source
```

The public API is what `fastapi_locale` exports, together with the `fastapi_locale.testing` plugin and the
command (ADR-0011). A module without a leading underscore exports public names only; everything else
lives in underscore modules. A unit test pins the exported names.

## 3. Layering rules

![Module dependencies](../diagrams/module-dependencies.svg)

1. Core modules (`_locale`, `_accept_language`, `_catalog`, `_translator`, `_formatting`, `_context`,
   `_errors_catalog`, `_openapi`, `exceptions`) never import FastAPI, Starlette or Pydantic.
   `config` belongs to the integration layer because it holds locale sources, which read Starlette's
   `HTTPConnection`. The core receives plain values from it.
2. Core modules never import integration modules.
3. There are no import cycles.

These rules are checked in CI with import-linter (ADR-0010).

## 4. Class design

![Design class diagram](../diagrams/class-design.svg)

### 4.1 LocaleConfig

A frozen dataclass, validated in `__post_init__`.

| Field | Type | Default | Rule |
| --- | --- | --- | --- |
| `default_locale` | `str` | required | Valid tag; must be in `supported_locales`. |
| `supported_locales` | `Sequence[str]` | required | At least one; valid tags; duplicates after normalization are an error. |
| `catalog_dirs` | `Sequence[str or PathLike]` | `()` | Paths; read when the `Localization` is created. |
| `default_domain` | `str` | `"messages"` | Non-empty; letters, digits, `_`, `-`, `.`. |
| `source_locale` | `str` | `"en"` | The language msgids are written in; needs no catalog (CAT-06). |
| `sources` | `Sequence[LocaleSource] or None` | `None` | `None` means query `lang`, then `Accept-Language` (ADR-0013). Each entry must be callable and not a class. |
| `builtin_catalogs` | `bool` | `True` | Load the library's catalogs: validation errors and FastAPI's schema text. |
| `localize_openapi` | `bool` | `True` | Serve the OpenAPI schema in the request's locale. |

Any rule violation raises `ConfigurationError` naming the field. A list field given a single string or
path is rejected, because iterating it would silently produce one entry per character.

The configuration is a value object and does no I/O. Tags are stored normalized, directories as `Path`.

### 4.2 Locale

A frozen dataclass with `tag`, `language`, `script`, `region`.

- `Locale.parse(value)` accepts `_` or `-` separators and any case, validates the BCP 47 shape
  (`language[-script][-region][-variant...]`), and normalizes: language lower case, script title case,
  region upper case (`zh_hant_tw` becomes `zh-Hant-TW`). Invalid input raises `ValueError`.
- `Locale.try_parse(value)` returns `None` instead of raising, for any value that is not a valid tag,
  including values that are not strings. Request input is parsed with it.
- `text_direction` comes from Babel's locale data.
- `str(locale)` is the tag. A locale is never equal to a string.

The internal function `truncations(locale)` yields the tag and then shorter tags, dropping single-letter
subtags with the subtag after them as RFC 4647 section 3.4 says: `zh-Hant-TW`, `zh-Hant`, `zh`.

### 4.3 Locale sources

```python
class LocaleSource(Protocol):
    def __call__(self, conn: HTTPConnection, /) -> str | Sequence[str] | None: ...
```

A source is any callable with this signature, so a plain function is one. Two optional attributes refine
it: `name` is recorded as `RequestLocale.decided_by` and defaults to the function or class name, and
`vary` lists the request headers the source reads.

| Source | Reads | `vary` | Returns |
| --- | --- | --- | --- |
| `QueryParamSource(param="lang")` | `?lang=hi` | `()` | `[value]` or `[]` |
| `CookieSource(cookie="locale")` | cookie | `("Cookie",)` | `[value]` or `[]` |
| `AcceptLanguageSource(max_length=1024)` | header | `("Accept-Language",)` | ranges by preference |
| `PathPrefixSource()` | `/hi/...` | `()` | planned (LOC-05) |

The default sources are the query parameter and `Accept-Language`. The cookie source is opt-in
(ADR-0013).

A source must be fast and must not do I/O. A source can never break a request: one that raises is logged
and skipped, and returned values that are not language tags are ignored. Sources are sync on purpose:
anything that needs I/O, like reading the user's profile, belongs in a dependency that calls
`set_locale()` (ADR-0004).

### 4.4 Accept-Language parsing

As shown in the activity diagram in the architecture document:

1. Join all `Accept-Language` header lines with `", "`.
2. If longer than `max_length`, cut at the last comma inside the limit.
3. Split members at commas. For each member, split the range from its parameters at `;`.
4. Skip empty ranges and `*`. If a `q` parameter exists and does not match the RFC 9110 qvalue grammar
   `0(\.\d{0,3})? | 1(\.0{0,3})?`, skip the member. Skip members with `q=0`.
5. Stable sort by `q`, highest first, so equal weights keep header order.

### 4.5 Negotiation

```text
for source in sources:
    for candidate in source(conn):
        locale = match(candidate)
        if locale: return locale, source.name
return default_locale, "default"

match(candidate):
    locale = Locale.try_parse(candidate)
    if locale is None: return None
    for tag in truncations(locale):                      # RFC 4647 lookup
        if tag in supported: return supported[tag]
    for other in supported, in configured order:         # same language, ADR-0012
        if other.language == locale.language and scripts do not conflict: return other
    return None
```

`supported` is a dictionary from normalized tag to `Locale`, built once. The result for a given candidate
list does not depend on anything but the configuration, so it is easy to test exhaustively. `set_locale()`,
`use_locale()` and `Localization.translator()` use the same `match`.

Matches are cached per input string in a bounded cache. A value that cannot be a tag, because it is not
a string or is longer than 64 characters, is refused before it reaches the cache, so request input cannot
fill it with large keys.

### 4.6 CatalogStore

`CatalogStore.load(supported, default, source, directories, builtin, default_domain)` receives plain
values from `LocaleConfig`, so the core never depends on the integration layer. It:

1. Build the directory list: the built-in `locales` directory first (if `builtin_catalogs`), then
   `config.catalog_dirs` in order.
2. For the built-in directory, read each `fastapi_locale.po` with Babel and compile it in memory. For each
   application directory, each supported locale, and each `<domain>.mo` file found under
   `<dir>/<locale dir>/LC_MESSAGES/`, parse it with the standard library's `gettext.GNUTranslations`.
   Locale directory names are matched to supported locales after normalization (`pt_BR` and `pt-BR` are
   the same).
3. A built-in regional catalog also serves its bare language when no catalog ships for that language, so
   an application that supports `pt` or `pt-PT` gets the `pt-BR` messages.
4. Merge catalogs for the same locale and domain in directory order, so later directories win (CAT-04).
5. For each supported locale and domain, build the fallback chain: the locale's own catalog, then catalogs
   for each shorter tag from `truncations()`, then the default locale's catalogs. A missing link is
   skipped. The end of the chain returns the msgid.
6. A locale in the source language gets no default-locale catalogs in its chain. Its messages are the
   msgids, so falling through would answer in the default language instead.
7. Build one `Translator` per supported locale.
8. Log the loaded locales, domains and message counts at INFO. Log a WARNING for a supported locale, other
   than the source locale, that has no catalog in the default domain.

A directory that does not exist, and any failure to read or parse a file, is raised as `CatalogLoadError`
with the path. The parser fails in several ways (`OSError`, `struct.error`, `LookupError` for an unknown
charset, `ValueError` for a bad plural rule); all of them are reported the same way.

### 4.7 Translator

Immutable. Holds its `Locale` and a mapping from domain to fallback chain.

| Method | Signature |
| --- | --- |
| `gettext` | `(message, /, **params) -> str` |
| `ngettext` | `(singular, plural, n, /, **params) -> str` |
| `pgettext` | `(context, message, /, **params) -> str` |
| `npgettext` | `(context, singular, plural, n, /, **params) -> str` |
| `dgettext` | `(domain, message, /, **params) -> str` |
| `dngettext` | `(domain, singular, plural, n, /, **params) -> str` |
| `dpgettext` | `(domain, context, message, /, **params) -> str` |
| `dnpgettext` | `(domain, context, singular, plural, n, /, **params) -> str` |

Positional-only message arguments leave every keyword name free for placeholders. In plural functions `n`
is also available as the placeholder `{n}` unless `params` sets it; `n` must be an integer, and anything
else raises `TypeError` in every locale. An unknown domain behaves like an empty catalog. A lookup without
`n` of an entry that has plural forms returns its form for one, as gettext does. The module-level
functions of the same names call the active translator.

Applications do not create translators; the constructor is internal.

### 4.8 Message formatting

`format_message(template, params)` replaces `{identifier}` with `str(params[identifier])`, turns `{{` and
`}}` into literal braces, and leaves anything else untouched. A missing name is left as written and logged
once per message and locale (ADR-0007).

Every translation function formats its result, whether or not the call passes values, so braces behave
the same everywhere. Schema text for OpenAPI is the exception: it is looked up as written (section 4.17).

### 4.9 Locale context

```python
_current: ContextVar[RequestLocale | None]

def get_locale() -> Locale: ...
def get_translator() -> Translator: ...
def set_locale(locale: str | Locale) -> Locale: ...
def use_locale(locale: str | Locale) -> ContextManager[Locale]: ...
```

- `get_translator()` returns, in order: the innermost `use_locale()` translator, the request's translator,
  the process default `Localization`'s default translator. With none of them it raises
  `LocalizationNotConfiguredError`.
- `set_locale()` works only inside a request. It resolves the value with the same lookup as negotiation
  (so `hi-IN` becomes `hi`), changes the `RequestLocale` in place, records `set_locale` as what decided
  it, and returns the locale. An unsupported value, which includes `None` and an empty string, raises
  `UnsupportedLocaleError`. Outside a request it raises `NoActiveRequestError` with a hint to use
  `use_locale()`.
- `use_locale()` sets a new `RequestLocale` for the block, yields the matched locale, and restores the
  previous value with its token, also when the block raises. It does not change the response's
  `Content-Language`.
- The process default is the `Localization` that was installed last, or the one that last called
  `Localization.make_default()`.

`RequestLocale` is public as the type of `request.state.locale`. It exposes two read-only properties,
`locale` and `decided_by`; everything else on it is internal.

### 4.10 LocaleMiddleware

Pure ASGI. For `http` and `websocket` scopes:

1. If the same localization already opened this request further out, as happens when a mounted
   application has it installed too, pass the call through. One `RequestLocale` serves the whole request.
2. If a test override is active on the `Localization`, use it; otherwise run negotiation.
3. Create a `RequestLocale`, store it in `scope["state"]["locale"]`, and set the context variable.
4. Call the application with a wrapped `send`. On `http.response.start`, add `Content-Language` with the
   current locale unless the application already set one, and merge the union of all sources' `vary`
   values into the response's `Vary` header lines, without duplicates and ignoring case.
5. Reset the context variable in `finally`.

`lifespan` scopes pass through untouched.

### 4.11 LazyText

As decided in ADR-0005.

| Behaviour | Rule |
| --- | --- |
| `str(x)`, `format(x, spec)` | Translate with the active translator, then apply `spec`. |
| `x == y` | True only for another `LazyText` with the same message, plural, n, context, domain and params. |
| `hash(x)` | Hash of message, plural, context and domain. Params are left out so unhashable values are allowed. |
| `repr(x)` | `LazyText('Item not found')`, never translated. |
| Pydantic validation | Accepts `LazyText` (kept) or `str` (kept as `str`). |
| Pydantic serialization | JSON mode: `str(x)`. Python mode: `x` itself. |
| JSON schema | `{"type": "string"}` |
| `jsonable_encoder` | Registered in `ENCODERS_BY_TYPE` as `str`. |
| `Any` and `object` positions | `__pydantic_serializer__` renders `str(x)`, for routes FastAPI serializes with Pydantic. |
| Pickle | `__reduce__` stores the constructor arguments. |

Each translation function has a lazy variant with the same arguments, including the four that name a
domain (`dgettext_lazy` and the others).

`LazyText` does not support `+`, `%` or slicing. Code that needs a string calls `str()` at the point where
the locale is known.

### 4.12 Error localization

`ErrorTemplate(type, message, plural=None, count_key=None, fallback=None)`. The table in
`_errors_catalog.py` has one entry per pydantic-core error type. Examples:

| type | message | plural | count_key |
| --- | --- | --- | --- |
| `missing` | `Field required` | | |
| `greater_than` | `Input should be greater than {gt}` | | |
| `string_too_short` | `String should have at least {min_length} character` | `String should have at least {min_length} characters` | `min_length` |
| `value_error` | `Value error, {error}` | | |

`ErrorLocalizer.localize(errors, translator)` returns new dictionaries. For each error (ADR-0014):

1. Find the template for `error["type"]`. If none, keep the error as it is.
2. Take the values from `ctx`, leaving out those that are `None`. If the template needs a value the error
   does not carry, try the template's `fallback`; with none left, keep the error as it is. `too_long` has a
   fallback for inputs whose actual length Pydantic does not report.
3. Look the template up with the error type as context, in the plural form chosen by `ctx[count_key]` when
   that is an integer. If no catalog in the chain translates it, keep the error as it is: Pydantic's own
   message is the source-language text.
4. Fill placeholders from `ctx`. Numbers are written as Pydantic writes them: `2`, not `2.0`, and no
   exponent.
5. Replace `msg`; copy every other key unchanged.

### 4.13 Exception handlers

`validation_exception_handler(request, exc)` returns
`JSONResponse(status_code=422, content={"detail": jsonable_encoder(localized_errors)})`, the same shape as
FastAPI's default.

`http_exception_handler(request, exc)` mirrors FastAPI's default: no body for status codes that do not
allow one, otherwise `{"detail": jsonable_encoder(exc.detail)}` with the exception's headers. Running
`detail` through `jsonable_encoder` is what renders `LazyText`.

`install()` registers both, but leaves alone any handler the application registered earlier for the same
exception. Applications with their own handlers can call these functions from them.

### 4.14 Localization

```python
class Localization:
    def __init__(self, config: LocaleConfig) -> None: ...     # loads catalogs
    config: LocaleConfig
    def install(self, app: FastAPI) -> None: ...               # middleware, handlers, app.state
    def make_default(self) -> None: ...                        # process default for non-request code
    def translator(self, locale: str | Locale) -> Translator: ...
    def override(self, locale: str | Locale) -> ContextManager[Locale]: ...   # tests
```

`install()` adds the middleware first, because Starlette refuses new middleware once the application has
started; nothing else is registered if that fails. It then stores the localization as
`app.state.localization`, registers the handlers, localizes the OpenAPI schema and makes the localization
the process default. It is idempotent for the same application and raises `ConfigurationError` if the
application already has a different `Localization`. Each FastAPI application has its own exception
handlers, so a mounted application needs its own `install()` call.

Negotiation, the catalog store and the `Vary` list are internal to the class and used by the middleware.

### 4.15 Dependencies

```python
LocaleDep = Annotated[Locale, Depends(current_locale)]
TranslatorDep = Annotated[Translator, Depends(current_translator)]
```

The providers `current_locale` and `current_translator` are small async functions that read the locale
context. They are async because FastAPI runs sync dependencies in its thread pool, which would add a
thread hop to every request. `app.dependency_overrides[current_translator]` replaces them in tests
(DI-03).

### 4.16 Exceptions

```text
LocalizationError
    ConfigurationError
    CatalogLoadError
    UnsupportedLocaleError
    LocalizationNotConfiguredError
    NoActiveRequestError
```

All carry a message that names what to change. None of them is raised because of request input.

### 4.17 OpenAPI localization

`translate_schema(schema, translator, builtin_domain)` returns a copy of the schema with these rules:

- String values of `title`, `summary` and `description` keys are translated at any depth.
- Values under `default`, `example`, `const` and `enum`, and everything under a key that starts with
  `x-`, are application data and are copied unchanged.
- `examples` is data when it is a list. When it is a mapping of OpenAPI Example Objects, their `summary`
  and `description` are translated and their `value` is not.
- The values of an OAuth `scopes` mapping are descriptions and are translated.
- The keys of `properties`, `responses`, `parameters`, `schemas` and the other mappings of names are
  chosen by the application. They are never read as keywords, so a field called `default` or a response
  called `default` is handled like any other.

Each text is looked up as written, with no placeholder formatting: first under the `openapi` context,
then without context, then in the built-in catalog under the `openapi` context, which holds FastAPI's own
strings (`OPENAPI_MESSAGES`). The first translation found wins.

`localize_openapi(app)` replaces `app.openapi` with a function that asks FastAPI for the schema and
keeps one translated copy per locale. FastAPI builds its one schema inside a default-locale block, so text
rendered during the build, such as a lazy default value, does not depend on which request came first. When
FastAPI returns a new schema object, the translated copies are dropped. `install()` calls
`localize_openapi` unless `localize_openapi=False`; calling it twice is harmless.

## 5. Public API example

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from fastapi_locale import LazyText, LocaleConfig, Localization, TranslatorDep, gettext_lazy

i18n = Localization(LocaleConfig(default_locale="en", supported_locales=["en", "hi", "de"],
                                 catalog_dirs=["app/locales"]))
app = FastAPI()
i18n.install(app)

NOT_FOUND = gettext_lazy("Item not found")


class Item(BaseModel):
    name: str
    status: LazyText = gettext_lazy("Pending")


@app.get("/items/{item_id}")
def read_item(item_id: int, tr: TranslatorDep) -> Item:
    if item_id != 1:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return Item(name=tr.gettext("Sample item"))
```

## 6. Testing helpers

- `Localization.override("hi")` forces every request in the block to `hi`.
- `use_locale("hi")` for code called directly.
- The pytest plugin, enabled with `pytest_plugins = ["fastapi_locale.testing"]`, adds a
  `@pytest.mark.locale("hi")` marker that runs the test body inside `use_locale`. It also restores the
  process default after each test. It is opt-in so installing the library never changes other projects'
  test runs.

## 7. Command line tool

`fastapi-locale <command>`, configured in `pyproject.toml`:

```toml
[tool.fastapi-locale]
sources = ["app"]
catalog_dir = "app/locales"
default_domain = "messages"
exclude = ["tests"]
```

An unknown key, a source directory that does not exist, or a domain that is not a valid file name is a
configuration error.

| Command | Action |
| --- | --- |
| `extract` | Write one template per domain, `<catalog_dir>/<domain>.pot`, from `sources`. |
| `init --locale TAG` | Create a `.po` file per template for a new locale, with CLDR plural rules. |
| `update` | Merge each template into every `.po` file of its domain. |
| `compile` | Compile every `.po` to `.mo`, in every domain; `--strict` fails on fuzzy entries. |
| `check` | Report stale, missing, fuzzy and obsolete entries, missing `Plural-Forms`, and placeholder mismatches. |

Exit codes: 0 success, 1 problems found, 2 usage or configuration error.

Extraction uses Babel's Python extractor and a table of the translation functions with the positions of
their domain, context, msgid and plural arguments: `gettext`, `ngettext`, `pgettext`, `npgettext`, the
four `d` variants, the `_lazy` variant of each, `gettext_noop` and `_`. A message is written to the
template of its domain, which must be a string literal and a valid file name; other calls are reported
and skipped. Hidden directories, `__pycache__`, `node_modules`, `site-packages`, virtual environments and
paths matching `exclude` are not scanned.

A template is rewritten only when its content changes; the creation date alone never causes a rewrite.
A catalog whose domain has no template, such as an override of the built-in messages, is compiled and is
checked for everything that does not need the sources.

## 8. Logging

| Event | Level | Fields |
| --- | --- | --- |
| Catalogs loaded | INFO | locales, domains, message count, directories |
| Supported locale without catalog | WARNING | locale, domain |
| Missing placeholder value | WARNING | locale, domain, msgid, placeholder (once per combination) |
| Custom source raised | WARNING | source name, exception type |
| Locale resolved | DEBUG | source name, locale |

Logger name: `fastapi_locale`. Message parameters and header values are never logged above DEBUG.

## 9. Compatibility

| Dependency | Supported range | Notes |
| --- | --- | --- |
| Python | 3.11 and later (see SRS section 7) | `tomllib` in the standard library is used by the CLI. |
| FastAPI | versions within upstream support; lower bound set by the CI matrix | |
| Pydantic | 2.x | v1 is out of scope. |
| Babel | 2.12 and later | |

## 10. Traceability

| Requirement group | Design sections |
| --- | --- |
| CAT | 4.1, 4.6 |
| LOC | 4.2 to 4.5, 4.9, 4.10 |
| TRN | 4.7 to 4.9 |
| LZY | 4.11 |
| ERR | 4.12, 4.13 |
| DI | 4.14, 4.15 |
| CLI | 7 |
| TST | 6 |
| DOC | 4.17 |
| NFR-03 to NFR-06 | 4.2, 4.4, 4.8 |
| NFR-10 | 8 |
