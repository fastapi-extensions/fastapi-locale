# ADR-0008: Load catalogs when the application is set up

- Status: Accepted
- Accepted: 2026-09-28
- Date: 2026-09-26

## Context

Catalogs must be loaded before the first request, and no file access may happen while a request is being
handled (C-03). The first draft of the SRS said "at startup (lifespan)".

## Options considered

1. **In the ASGI lifespan startup event.** Fits the idea of startup, but FastAPI applications set their own
   `lifespan`, and combining two is awkward. Starlette's `TestClient` also skips lifespan unless it is used
   as a context manager, so tests would see unloaded catalogs.
2. **On the first request.** Adds latency to that request and does file access during request handling.
   Rejected.
3. **When `Localization` is created.** Catalogs load when the application module builds its
   `Localization(config)`, before the server accepts connections.

## Decision

Use option 3. Loading is fast (it reads compiled `.mo` files), and a failure raises `CatalogLoadError` at
import time, so a broken deployment never starts. The SRS requirement CAT-03 is worded to match: catalogs
are loaded during application setup, before the first request.

## Consequences

- Works the same with or without lifespan, in tests and in production.
- Errors appear at import, which is where developers look first.
- Importing the application module reads files. This is the same as most configuration loading and is
  documented.

## Related requirements

C-03, CAT-03, CAT-05
