# Software Requirements Specification

| Field | Value |
| --- | --- |
| Project | fastapi-locale (working name) |
| Document | Software Requirements Specification (SRS) |
| Version | 1.0 |
| Status | Approved |
| Owner | Kapil Dagur |
| Last updated | 2026-09-28 |

## 1. Introduction

### 1.1 Purpose

This document states what fastapi-locale must do and how well it must do it. It is the basis for the
domain model, the architecture and design documents, and the test plan. Each requirement has an ID so
design decisions and tests can point back to it.

### 1.2 Product scope

fastapi-locale is an internationalization (i18n) and localization (l10n) library for FastAPI. It picks a
locale for each request and translates application messages with GNU gettext catalogs. It also returns
FastAPI's validation errors and HTTP errors in the client's language.

It follows the i18n practices that Django established (per-request activation, lazy translation, message
extraction and compilation) and exposes them the way FastAPI users expect: dependency injection,
Pydantic models, and a test-friendly setup.

The research behind the scope is in [Existing libraries](../research/existing-libraries.md).

### 1.3 Definitions

| Term | Meaning |
| --- | --- |
| Locale | A language, optionally with region or script, written as a BCP 47 tag such as `hi`, `pt-BR`, `zh-Hant`. |
| Catalog | A compiled gettext message file (`.mo`) for one locale and one domain. |
| Domain | A named group of messages, such as `messages` for the application and a separate domain for this library. |
| msgid | The source text of a message, used as the lookup key. |
| Lazy text | A value that holds a msgid and is translated only when it is rendered. |
| Locale source | One place a locale can come from: path, query parameter, cookie, header, user preference. |
| Fallback chain | The ordered list of locales tried when looking up a message, for example `hi-IN`, `hi`, then the default. |
| Validation error | An entry in FastAPI's 422 response, produced by Pydantic, with `type`, `loc`, `msg`, `input` and `ctx`. |

### 1.4 References

- RFC 9110, HTTP Semantics, section 12.5.4 (Accept-Language) and 12.5.5 (Vary)
- RFC 4647, Matching of Language Tags (lookup scheme)
- BCP 47, Tags for Identifying Languages
- GNU gettext manual (PO/MO formats, plural forms)
- Unicode CLDR plural rules, as shipped with Babel
- Django documentation, Internationalization and localization
- Pydantic documentation, Validation errors
- FastAPI documentation, Handling errors and Dependencies

## 2. Overall description

### 2.1 Product perspective

fastapi-locale is a library that a FastAPI application installs and configures. It is not a service.
It sits between the ASGI server and the application's routes and interacts with:

- Starlette's ASGI middleware stack, to resolve the locale once per request
- FastAPI's dependency system, to expose the locale and a translator to route code
- FastAPI's exception handlers, to localize 422 and HTTP error responses
- Pydantic's core schema hooks, so lazy text can live in models and serialize correctly
- Babel, for catalog loading, plural rules and the message extraction tooling

It is planned as part of the `fastapi-extensions` GitHub organization, next to fastapi-tenancy.

### 2.2 User classes

| User class | Description | Main needs |
| --- | --- | --- |
| API developer | Builds a FastAPI service and adds this library. | Small setup, clear API, testable, no surprises in production. |
| Translator | Edits `.po` files, often not a Python developer. | Standard gettext files that work with Poedit, Weblate and similar tools. |
| API client | A browser, mobile app or other service calling the API. | Responses in the requested language, stable error `type` codes. |
| Library maintainer | Keeps the library working across FastAPI and Pydantic releases. | Tests that catch upstream changes early. |

### 2.3 Use cases

These are expanded in the [use case model](../modeling/use-case-model.md).

| ID | Use case | Primary actor |
| --- | --- | --- |
| UC-01 | Receive a response in the preferred language | API client |
| UC-02 | Receive validation errors in the preferred language | API client |
| UC-03 | Translate a message in route or service code | API developer |
| UC-04 | Put translatable text in a Pydantic model or HTTPException | API developer |
| UC-05 | Use a signed-in user's saved language | API developer |
| UC-06 | Extract, translate and compile message catalogs | API developer, Translator |
| UC-07 | Test routes under a fixed locale | API developer |
| UC-08 | Read the API documentation in a chosen language | API client |
| UC-09 | Verify catalogs are up to date | CI pipeline |

### 2.4 Operating environment

- CPython 3.11 or later (see open issue OI-01)
- FastAPI and Starlette versions still supported upstream; the exact lower bounds are set in the design
- Pydantic v2 only
- Any ASGI server (Uvicorn, Hypercorn, Granian)
- Linux, macOS and Windows

### 2.5 Constraints

- C-01: Catalogs use the GNU gettext PO/MO formats so existing translation tools work unchanged.
- C-02: Locale state is held in `contextvars`, not thread locals or globals, so it is correct under asyncio
  and in FastAPI's thread pool.

- C-03: No network access and no file access during request handling. Catalogs are loaded at startup.
- C-04: Runtime dependencies are limited to FastAPI (with Starlette and Pydantic) and Babel.
- C-05: The public API is fully typed and passes `mypy --strict`. The package ships `py.typed`.

### 2.6 Assumptions and dependencies

- A-01: Applications write msgids in one source language, usually English.
- A-02: Pydantic keeps error `type` codes and `ctx` keys stable within a major version. Message wording
  may change and the library must not depend on it.

- A-03: Babel keeps shipping CLDR plural rules and the `pybabel` extraction tooling.

## 3. Functional requirements

Priority uses MoSCoW: M (must), S (should), C (could). Release is the first version expected to meet the
requirement: 0.1 is the first public release, "later" is after 0.1.

### 3.1 Catalogs (CAT)

| ID | Requirement | Priority | Release |
| --- | --- | --- | --- |
| CAT-01 | The library shall load compiled `.mo` catalogs from one or more directories laid out as `<dir>/<locale>/LC_MESSAGES/<domain>.mo`. | M | 0.1 |
| CAT-02 | The library shall support multiple domains, and a message lookup shall name its domain or use the default one. | M | 0.1 |
| CAT-03 | Catalogs shall be loaded once during application setup, before the first request is served. | M | 0.1 |
| CAT-04 | When the same locale and domain appear in more than one directory, entries from later directories shall override earlier ones. | S | 0.1 |
| CAT-05 | Startup shall fail with a clear error if a configured directory is missing or a catalog cannot be parsed. | M | 0.1 |
| CAT-06 | The default locale shall not need a catalog when it is the source language. | M | 0.1 |
| CAT-07 | The library shall be able to reload catalogs without restarting the process, for use in development. | C | later |

### 3.2 Locale resolution (LOC)

| ID | Requirement | Priority | Release |
| --- | --- | --- | --- |
| LOC-01 | The library shall resolve one locale per HTTP request before any route, dependency or exception handler runs. | M | 0.1 |
| LOC-02 | The set of supported locales shall be configured explicitly. A request shall never resolve to a locale outside that set. | M | 0.1 |
| LOC-03 | Locale sources shall be configurable and tried in order. The first source that yields a supported locale wins; if none does, the default locale is used. | M | 0.1 |
| LOC-04 | Built-in sources shall include query parameter, cookie and `Accept-Language` header. | M | 0.1 |
| LOC-05 | A path prefix source (for example `/hi/items`) shall be available. | C | later |
| LOC-06 | Applications shall be able to add their own source as a plain callable. | M | 0.1 |
| LOC-07 | `Accept-Language` shall be parsed per RFC 9110, including q-values, and entries with `q=0` shall be treated as refused. | M | 0.1 |
| LOC-08 | Matching shall follow RFC 4647 lookup: a requested `hi-IN` falls back to `hi` when only `hi` is supported. | M | 0.1 |
| LOC-09 | Tags shall be normalized so `pt_BR`, `pt-br` and `pt-BR` are treated as the same locale. | M | 0.1 |
| LOC-10 | Responses shall carry `Content-Language` with the resolved locale. | M | 0.1 |
| LOC-11 | Responses shall carry a `Vary` header naming every request header the configured sources read (for example `Accept-Language`, `Cookie`), merged with any existing `Vary` value. | M | 0.1 |
| LOC-12 | WebSocket connections shall have a locale resolved the same way as HTTP requests. | S | 0.1 |
| LOC-13 | An application shall be able to change the locale for the rest of a request, for example after loading the signed-in user's saved language in a dependency. | M | 0.1 |
| LOC-14 | The resolved locale shall remain active in background tasks started by the request. | S | 0.1 |
| LOC-15 | Code running outside a request (startup, scripts, workers) shall see the configured default locale. | M | 0.1 |

### 3.3 Translation API (TRN)

| ID | Requirement | Priority | Release |
| --- | --- | --- | --- |
| TRN-01 | The library shall provide `gettext`, `ngettext`, `pgettext` and `npgettext` that translate in the active locale. | M | 0.1 |
| TRN-02 | Plural selection shall use the plural rules of the target locale, not English rules. | M | 0.1 |
| TRN-03 | Named placeholders shall be supported so translators can reorder them, for example `{name}` and `{count}`. | M | 0.1 |
| TRN-04 | A missing translation shall fall back through the fallback chain and finally return the msgid, without raising. | M | 0.1 |
| TRN-05 | A context manager shall switch the active locale for a block of code and restore the previous one on exit, including on error. | M | 0.1 |
| TRN-06 | The same functions shall be usable from both async and sync code, including code running in FastAPI's thread pool. | M | 0.1 |

### 3.4 Lazy text (LZY)

| ID | Requirement | Priority | Release |
| --- | --- | --- | --- |
| LZY-01 | The library shall provide lazy variants of the functions in TRN-01. | M | 0.1 |
| LZY-02 | Lazy text shall be translated when it is serialized, using the locale active at that moment. | M | 0.1 |
| LZY-03 | Lazy text shall be usable as a Pydantic model field value and serialize to a JSON string. | M | 0.1 |
| LZY-04 | Lazy text shall serialize correctly through FastAPI's `jsonable_encoder` and response models. | M | 0.1 |
| LZY-05 | Lazy text shall be usable as `HTTPException.detail`. | M | 0.1 |
| LZY-06 | Lazy text shall compare, hash and format predictably. The exact rules are set in the design. | M | 0.1 |

### 3.5 Validation and HTTP errors (ERR)

| ID | Requirement | Priority | Release |
| --- | --- | --- | --- |
| ERR-01 | The library shall provide an exception handler that returns FastAPI's 422 response with each `msg` translated into the request locale. | M | 0.1 |
| ERR-02 | Translation shall be keyed on the Pydantic error `type` and filled from `ctx`, never on the English `msg` text. | M | 0.1 |
| ERR-03 | The 422 response shape shall stay the same as FastAPI's default. Only `msg` changes; `type`, `loc`, `input` and `ctx` are left as they are. | M | 0.1 |
| ERR-04 | Errors whose message depends on a number (for example `min_length`) shall use the target locale's plural rules. | M | 0.1 |
| ERR-05 | The library shall ship a message template covering every error `type` of the supported pydantic-core versions. | M | 0.1 |
| ERR-06 | Applications shall be able to override any built-in error message through their own catalog. | M | 0.1 |
| ERR-07 | An error `type` with no entry shall fall back to Pydantic's original `msg`. | M | 0.1 |
| ERR-08 | Messages from custom validators (`ValueError`, `PydanticCustomError`) that the application translated shall be passed through, and the Pydantic prefix such as `Value error,` shall be localized. | S | 0.1 |
| ERR-09 | The library shall provide an HTTP exception handler that renders lazy `detail` values in the request locale. | M | 0.1 |
| ERR-10 | The library shall ship translations of the error messages for an initial set of languages (see OI-04). | S | 0.1 |
| ERR-11 | Numbers in error messages shall be formatted for the locale (for example `1.000,5` in German). | C | later |

### 3.6 FastAPI integration (DI)

| ID | Requirement | Priority | Release |
| --- | --- | --- | --- |
| DI-01 | A single setup call shall register the middleware, exception handlers and catalog loading on an application. | M | 0.1 |
| DI-02 | `Depends` providers shall give route code the active locale and a translator bound to it. | M | 0.1 |
| DI-03 | These providers shall be replaceable through `app.dependency_overrides`. | M | 0.1 |
| DI-04 | The library shall not rely on process-wide mutable state that prevents two applications with different settings from running in one process. | S | 0.1 |

### 3.7 Tooling (CLI)

| ID | Requirement | Priority | Release |
| --- | --- | --- | --- |
| CLI-01 | A command line tool shall extract messages into a `.pot` template, recognizing this library's function names including the lazy ones. | M | 0.1 |
| CLI-02 | It shall create a new locale's `.po` file, update existing `.po` files from the template, and compile `.po` to `.mo`. | M | 0.1 |
| CLI-03 | The tool shall read its settings from `pyproject.toml`. | S | 0.1 |
| CLI-04 | A check command shall exit non-zero when catalogs are out of date, have fuzzy or missing entries, or have translations whose placeholders differ from the msgid, for use in CI. | S | 0.1 |

### 3.8 Testing support (TST)

| ID | Requirement | Priority | Release |
| --- | --- | --- | --- |
| TST-01 | A pytest plugin shall provide a fixture that runs a test under a given locale. | M | 0.1 |
| TST-02 | Tests shall be able to force the request locale without crafting headers. | S | 0.1 |

### 3.9 API documentation (DOC)

| ID | Requirement | Priority | Release |
| --- | --- | --- | --- |
| DOC-01 | The OpenAPI schema shall be available per supported locale, with titles, summaries and descriptions translated. | S | later |
| DOC-02 | Each locale's schema shall be generated once and cached. | S | later |
| DOC-03 | Swagger UI and ReDoc shall be able to show the documentation for a chosen locale. | C | later |

### 3.10 Templates and formatting (FMT)

| ID | Requirement | Priority | Release |
| --- | --- | --- | --- |
| FMT-01 | Jinja2 templates shall be able to use the translation functions. | C | later |
| FMT-02 | Helpers shall format dates, times, numbers and currency for the active locale. | C | later |
| FMT-03 | A timezone shall be resolved per request in the same way as the locale. | C | later |

## 4. Non-functional requirements

| ID | Category | Requirement | Verification |
| --- | --- | --- | --- |
| NFR-01 | Performance | Locale resolution adds no more than 50 microseconds median per request on the reference benchmark. | Benchmark in CI |
| NFR-02 | Performance | A message lookup does no I/O and no per-call object creation beyond the result string. | Code review, benchmark |
| NFR-03 | Security | Values from path, query, cookie or header shall be validated as BCP 47 tags and matched only against the configured set. They shall never be used to build a file path. | Unit tests, review |
| NFR-04 | Security | `Accept-Language` input longer than a fixed limit shall be truncated before parsing to bound CPU cost. | Unit tests |
| NFR-05 | Security | Placeholder filling shall only substitute named values. A translated string shall not be able to read attributes or index into arguments (as `{obj.__class__}` would with `str.format`), because catalogs often come from outside contributors. | Unit tests |
| NFR-06 | Reliability | A missing translation or broken placeholder in a translated string shall never cause a 500. The library falls back to the msgid and logs a warning. | Unit tests |
| NFR-07 | Reliability | Locale state from one request shall never be visible in another, under concurrent async and threaded load. | Integration tests |
| NFR-08 | Compatibility | Every supported Python, FastAPI and Pydantic version combination is tested in CI. | CI matrix |
| NFR-09 | Compatibility | A test shall fail when a supported pydantic-core version has an error `type` missing from the built-in template. | Unit test |
| NFR-10 | Observability | The library logs through the standard `logging` module under one named logger, and does not log request bodies or personal data. | Review |
| NFR-11 | Maintainability | Line and branch coverage of at least 95 percent, `ruff` clean, `mypy --strict` clean. | CI |
| NFR-12 | Usability | A new user can localize 422 errors in an existing app with no more than five lines of setup, following the quick start. | Documentation review |
| NFR-13 | Documentation | Every public function and class is documented in the published reference docs, with a runnable example for each use case. | Docs build in CI |
| NFR-14 | Portability | The library runs unmodified on Linux, macOS and Windows. | CI matrix |

## 5. Out of scope

- Machine translation
- A web interface for managing translations
- Catalogs stored in a database or fetched over the network
- Translating data stored by the application (model content, user input)
- Pydantic v1

## 6. Verification

Each requirement is verified by at least one of: unit test, integration test against a running FastAPI
application, end-to-end test through a real ASGI server, benchmark, or review. The traceability matrix
that links requirement IDs to tests is kept in the test plan.

## 7. Resolved issues

| ID | Question | Resolution |
| --- | --- | --- |
| OI-01 | Minimum Python version | Python 3.11. Python 3.10 reaches end of life in October 2026. |
| OI-02 | License | MIT, the same as fastapi-tenancy. |
| OI-03 | Package name | `fastapi-locale`, free on PyPI as of 2026-09-28. |
| OI-04 | Languages shipped for error messages | German, Spanish, French, Hindi and Portuguese (Brazil). Others by community contribution. |
| OI-05 | User preference and 422 errors | Resolved by [ADR-0004](../adr/0004-middleware-resolves-dependencies-refine.md): dependencies run before body validation, so a dependency that calls `set_locale()` also sets the language of 422 errors. |
