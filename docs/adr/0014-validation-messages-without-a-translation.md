# ADR-0014: Keep Pydantic's message when there is nothing to translate into

- Status: Accepted
- Accepted: 2026-10-04
- Date: 2026-10-04

## Context

ADR-0006 gives each error type an English template owned by the library. The handler rendered that
template for every request, including requests in the source language. Rendering English a second time
could not be kept identical to FastAPI's own output:

- Pydantic writes a float bound as `0`; rendering the context value in Python gave `0.0`, and large or
  small bounds came out with an exponent.
- For some inputs Pydantic reports no actual length and writes "not more"; the template showed `None`.
- FastAPI builds the error for a malformed JSON body itself, with its own message.
- An error without a value the template needs showed the raw placeholder to the client.

## Options considered

1. **Keep rendering the template and correct each difference as it is found.** The list grows with every
   Pydantic and FastAPI release.
2. **Replace `msg` only when a catalog translates the template.** Otherwise the error is returned as
   Pydantic or FastAPI produced it.

## Decision

Use option 2. This record adds to ADR-0006; the templates and their keys do not change.

- The template is looked up in the request locale's fallback chain. With no translation, the error keeps
  its original `msg`. In the source language the response is the one FastAPI returns.
- An error that lacks a value the template needs keeps its original `msg`. A template may name a fallback
  template for that case; `too_long` has one for an unknown length.
- Numbers from the context are written as Pydantic writes them.

## Consequences

- The English templates are msgids only. Their wording can lag behind Pydantic's without any effect on
  English responses.
- An application can still reword the source language by shipping a `fastapi_locale` catalog for it.
- A locale with no built-in catalog shows Pydantic's English, as before.
- A translation is used only when the error carries every value it needs, so a client never sees a raw
  placeholder because of a change in Pydantic.

## Related requirements

ERR-02, ERR-03, ERR-07, NFR-06
