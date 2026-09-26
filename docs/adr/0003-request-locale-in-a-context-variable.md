# ADR-0003: Hold the request locale in a context variable with a per-request holder

- Status: Proposed
- Date: 2026-09-26

## Context

Code deep inside a request (a service function, a Pydantic serializer, a background task) needs to know
the request's locale without it being passed through every call. FastAPI runs async code on the event
loop and sync code in a thread pool, and many requests run at the same time.

Experiments with FastAPI 0.141.1 showed:

- A value set in a `ContextVar` by pure ASGI middleware is visible in sync dependencies, the endpoint,
  exception handlers and background tasks.
- A value set with `ContextVar.set()` inside a dependency or a sync endpoint is **not** visible to
  exception handlers or response serialization, because those run in a different context copy.

## Options considered

1. **Thread-local or global state.** Wrong under asyncio: concurrent requests on one thread overwrite
   each other. Rejected.
2. **`request.state` only.** Safe, but code without the `Request` object cannot reach it, which rules out
   lazy text and plain `gettext()` calls.
3. **`ContextVar` holding the locale value.** Safe and reachable everywhere, but changes made in a
   dependency are lost, as the experiment shows.
4. **`ContextVar` holding a small mutable per-request object (`RequestLocale`).** The middleware creates
   one object per request and sets it once. Later changes modify the object, so every context copy that
   refers to it sees them.

## Decision

Use option 4. The middleware creates a `RequestLocale`, sets it in a module-level `ContextVar` and resets
the variable with its token when the request ends. `set_locale()` changes the object in place.
`use_locale()` sets a new, separate object for the length of a block and restores the previous one with its
token.

The `RequestLocale` is also stored in the ASGI scope so code that has the `Request` can reach it
explicitly.

## Consequences

- Correct under asyncio and in the thread pool (C-02, NFR-07).
- Changes made by the user's dependency reach the 422 handler and the `Content-Language` header
  (see ADR-0004).
- Tasks started with `asyncio.create_task` inside a request share the object. A change by one task is seen
  by the others. This is the intended behaviour for one request and is documented.
- Several applications in one process each create their own holders, so they do not interfere (DI-04).

## Related requirements

C-02, LOC-01, LOC-13, LOC-14, LOC-15, TRN-05, TRN-06, DI-04, NFR-07
