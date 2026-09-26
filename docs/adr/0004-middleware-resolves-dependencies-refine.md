# ADR-0004: Resolve the locale in middleware and let dependencies refine it

- Status: Proposed
- Date: 2026-09-26

## Context

FastAPI developers expect dependency injection, so resolving the locale in a dependency looks natural.
But a locale must also be available where no route dependency runs: the 422 validation handler, HTTP
exception handlers, and the response headers.

Many applications also store a preferred language on the user. The user is usually loaded in an auth
dependency, which runs after any middleware. This was open issue OI-05 in the SRS.

Experiments with FastAPI 0.141.1 showed:

- A locale set only in an app-level dependency (as fastapi-i18n does) is missing in the 422 handler.
- FastAPI runs a route's sub-dependencies before it validates the endpoint's own body and parameters. A
  `current_user` dependency that changes the per-request holder (ADR-0003) is therefore seen by the 422
  handler when the body is invalid, and by the middleware when it writes `Content-Language`.

## Options considered

1. **Dependency only.** Idiomatic, but 422 errors and exception handlers would ignore the locale. Rejected.
2. **Middleware only.** Always available, but middleware cannot use the user that a dependency loads.
3. **Middleware resolves, dependencies may refine.** The middleware resolves from the request (query,
   cookie, header). An application dependency may call `set_locale()` to replace it for the rest of the
   request.
4. **The 422 handler calls an async user hook** to look up the user's language. Duplicates the
   application's auth logic inside an error handler, and runs it twice per request.

## Decision

Use option 3. `LocaleMiddleware`, a pure ASGI middleware (not `BaseHTTPMiddleware`), resolves the locale
before routing. Dependencies read it through `LocaleDep` and `TranslatorDep` and can change it with
`set_locale()`.

## Consequences

- Localized 422 errors work with no extra setup, and they follow the user's language when the
  application sets it in a dependency.
- Known limit: if the user dependency's own parameters fail validation (for example a malformed
  `Authorization` header parameter), that dependency does not run and the response uses the locale from the
  request. The user guide will state this.
- WebSocket connections get the same resolution (LOC-12).
- Pure ASGI middleware avoids the known context and streaming problems of `BaseHTTPMiddleware`.

## Related requirements

LOC-01, LOC-10, LOC-11, LOC-12, LOC-13, ERR-01, DI-02, DI-03
