# Test plan

| Field | Value |
| --- | --- |
| Document | Test plan |
| Version | 1.0 |
| Status | Approved |
| Owner | Kapil Dagur |
| Last updated | 2026-09-28 |

## 1. Purpose

This plan states how fastapi-locale is verified: which test levels exist, what each covers, where they run,
and which tests prove each requirement. It covers the first release (0.1).

## 2. Test levels

The suite follows the testing pyramid. Most tests are fast unit tests of the core; fewer tests run a real
FastAPI application; a small number run a real server over the network.

| Level | Marker | Scope | Tools | Speed |
| --- | --- | --- | --- | --- |
| Unit | `unit` | One module in isolation, mostly the framework-free core. No I/O except temporary catalog files. | pytest, Hypothesis | milliseconds |
| Integration | `integration` | The library inside a FastAPI application, called in process through the ASGI interface. | pytest, httpx `ASGITransport`, Starlette `TestClient` | tens of milliseconds |
| End-to-end | `e2e` | A real Uvicorn process serving an example application, called over TCP. Also the CLI run as a subprocess. | pytest, httpx, subprocess | seconds |
| Static | none | Lint, format, types, layering, security scan. | Ruff, mypy, import-linter, bandit | seconds |
| Benchmark | `benchmark` | Resolution and lookup cost (NFR-01, NFR-02). | pytest-benchmark | seconds |

The library talks to no external service, so no containers are needed for tests. The end-to-end level still
uses a real server process, because middleware ordering, header handling and concurrency behave slightly
differently there than in an in-process client.

## 3. Test design

### 3.1 Unit

- **Locale parsing and truncation.** Table-driven cases for valid and invalid tags, plus a Hypothesis
  property: `parse(str(parse(x))) == parse(x)` for any valid `x`, and `parse` never raises anything but
  `ValueError`.
- **Accept-Language parsing.** RFC 9110 examples, malformed members, `q=0`, wildcards, duplicate ranges,
  very long headers, and a Hypothesis property that the parser never raises on arbitrary text.
- **Negotiation.** Every branch of the resolution activity diagram: source order, invalid candidates,
  truncation, default fallback.
- **Catalog store.** Loading from temporary directories with `.mo` files compiled in the test: merge order,
  fallback chain, missing directory, corrupt file, locale directory name normalization.
- **Translator.** All eight functions, plural rules for languages with one, two, three and six forms,
  context, domains, missing entries.
- **Formatting.** Named substitution, escaped braces, missing names, attribute and index syntax left
  untouched (NFR-05).
- **Context.** `use_locale` nesting and restore on error, `set_locale` inside and outside a request,
  process default.
- **LazyText.** Equality, hashing, formatting, pickling, Pydantic validation and serialization, JSON schema.
- **Error localizer.** Templates exist for every error type of the installed pydantic-core (NFR-09); plural
  selection; unknown types; `value_error` prefix.
- **Config.** Every validation rule in the detailed design, section 4.1.

### 3.2 Integration

Each test builds a small FastAPI application with `Localization.install()`.

- Resolution from query, cookie and header; custom source; source order.
- `Content-Language` and `Vary` on normal responses, streaming responses, error responses, and when the
  application already set these headers.
- Localized 422 for body, query, path and header validation, with the response shape compared field by
  field against FastAPI's default handler.
- `set_locale()` in an async and in a sync dependency, seen by the endpoint, the 422 handler and the
  response header (ADR-0004).
- `HTTPException` with `LazyText` detail, nested detail, custom headers, and status codes without a body.
- Response models with `LazyText` fields; plain dict responses; OpenAPI generation still works.
- Background tasks see the request locale.
- WebSocket connections resolve a locale.
- `dependency_overrides` for `current_locale` and `current_translator`.
- `Localization.override()` and the pytest marker.
- Two applications with different configurations in one process (DI-04).
- Isolation: many concurrent requests with different locales through one application, checking that every
  response matches its own request (NFR-07).

### 3.3 End-to-end

- Start `examples/basic` under Uvicorn on a free port; run the same client scenarios as the quick start:
  translated responses, localized 422s in several languages, lazy `HTTPException` detail, headers.
- Concurrency: 200 parallel requests over TCP with mixed languages; every response is in its own language.
- CLI round trip in a temporary project: `extract`, `init`, edit the `.po`, `update`, `check` (fails on a
  missing translation, passes after it is added), `compile`, then load the result with `Localization`.

## 4. Environments

| Environment | Where | What runs |
| --- | --- | --- |
| Developer machine or dev container | local | All levels via `make` targets. |
| CI, pull requests | GitHub Actions, Ubuntu | Static checks; unit and integration on Python 3.11, 3.12, 3.13, 3.14; end-to-end on 3.12. |
| CI, compatibility | GitHub Actions | Unit and integration against the lowest supported FastAPI, Pydantic and Babel versions, installed over the locked test tools. |
| CI, portability | GitHub Actions, macOS and Windows | Unit and integration on one Python version (NFR-14). |

## 5. Entry and exit criteria

A change can be merged when:

- Ruff, mypy (strict), import-linter and bandit pass.
- All unit and integration tests pass on every Python version in the matrix.
- Line and branch coverage is at least 95 percent (NFR-11).
- New behaviour has tests at the lowest level that can prove it.

A release can be tagged when, in addition:

- End-to-end tests pass.
- The compatibility and portability jobs pass.
- The benchmark is within the NFR-01 budget.
- The docs build passes in strict mode.

## 6. Traceability

| Requirement | Unit | Integration | End-to-end |
| --- | --- | --- | --- |
| CAT-01, CAT-02, CAT-04 | `test_catalog.py` | | CLI round trip |
| CAT-03, CAT-05, CAT-06 | `test_catalog.py`, `test_config.py` | `test_setup.py` | |
| LOC-01 to LOC-04, LOC-06 | `test_negotiation.py` | `test_resolution.py` | basic scenarios |
| LOC-07 | `test_accept_language.py` | `test_resolution.py` | |
| LOC-08, LOC-09 | `test_locale.py`, `test_negotiation.py` | | |
| LOC-10, LOC-11 | | `test_headers.py` | basic scenarios |
| LOC-12 | | `test_websocket.py` | |
| LOC-13 | `test_context.py` | `test_user_locale.py` | |
| LOC-14 | | `test_background.py` | |
| LOC-15 | `test_context.py` | | |
| TRN-01 to TRN-06 | `test_translator.py`, `test_formatting.py`, `test_context.py` | `test_dependencies.py` | |
| LZY-01 to LZY-06 | `test_lazy.py` | `test_lazy_responses.py` | basic scenarios |
| ERR-01 to ERR-08 | `test_error_localizer.py` | `test_validation_errors.py` | basic scenarios |
| ERR-09 | | `test_http_errors.py` | basic scenarios |
| DI-01 to DI-04 | | `test_setup.py`, `test_dependencies.py` | |
| CLI-01 to CLI-04 | `test_cli_settings.py` | | CLI round trip |
| TST-01, TST-02 | | `test_testing_helpers.py` | |
| NFR-01, NFR-02 | benchmark | | |
| NFR-03, NFR-04 | `test_locale.py`, `test_accept_language.py` | `test_resolution.py` | |
| NFR-05, NFR-06 | `test_formatting.py`, `test_translator.py` | | |
| NFR-07 | | `test_isolation.py` | concurrency |
| NFR-09 | `test_error_localizer.py` | | |
| NFR-11 | coverage report in CI | | |

Requirements planned after 0.1 (CAT-07, LOC-05, ERR-11, DOC, FMT) get tests when they are scheduled.

## 7. Test data

- Catalogs used by tests are `.po` files under `tests/data/locales`, compiled to a temporary directory by a
  session fixture, so no binary files are committed.
- Languages chosen to cover plural rule families: English (2 forms), French (2, with 0 singular), Hindi (2),
  Russian (3), Arabic (6), Japanese (1), plus `pt-BR` and `pt` for fallback chains.

## 8. Risks

| Risk | Mitigation |
| --- | --- |
| Tests pass in process but fail behind a real server. | End-to-end level with Uvicorn over TCP. |
| Concurrency bugs that appear only under load. | Isolation tests with many concurrent mixed-locale requests at two levels. |
| Upstream releases break the library between our releases. | Scheduled weekly CI run against the latest FastAPI and Pydantic. |
