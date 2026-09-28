# ADR-0009: Localize OpenAPI by translating the generated schema

- Status: Accepted
- Accepted: 2026-09-28
- Date: 2026-09-26

## Context

Route summaries, descriptions and model field descriptions appear in the OpenAPI schema. FastAPI builds the
schema with Pydantic models whose fields are typed `str`, so lazy text there fails validation. FastAPI also
caches one schema per application.

## Options considered

1. **Lazy text in route and field metadata,** resolved while FastAPI builds the schema. Needs changes to
   FastAPI's schema generation, which is not an extension point. Rejected.
2. **Copy the routes with metadata translated, then call FastAPI's `get_openapi`** once per locale. Covers
   route metadata but not field descriptions, which come from Pydantic's JSON schema.
3. **Translate the finished schema.** Developers write plain English metadata and mark it for extraction
   with a no-op marker (`gettext_noop`). FastAPI generates the schema once. For each locale the library
   walks the schema and translates the values of `title`, `summary` and `description` keys through the
   catalog, then caches the result.

## Prototype results

A prototype against FastAPI 0.141 on 2026-09-28 showed:

- The app title and description, tag descriptions, operation summaries and descriptions, response
  descriptions, field titles and descriptions, and model titles were all translated.
- Swagger UI needs no changes: the browser sends `Accept-Language` when it fetches `/openapi.json`, the
  middleware resolves the locale, and the response carries `Content-Language` and `Vary`.
- Translating a 300-route schema (69 KB) took 1.5 ms, once per locale.
- A model titled `Item` was translated because the application also used the msgid `Item` elsewhere.
  `$ref` keys do not change, so nothing breaks, but translators need a way to tell the two apart.
- FastAPI's own text ("Successful Response", "Validation Error", the field titles of its
  `ValidationError` schema) needs translations the application should not have to write.
- FastAPI takes route descriptions from docstrings, which gettext tools cannot extract.

## Decision

Use option 3, with these refinements from the prototype:

- Look up each text with the `openapi` message context first, then without context, then in the
  library's built-in catalog, which ships FastAPI's own strings.
- Never translate values under `default`, `example`, `examples`, `const` and `enum`.
- Translate each locale once, on first use, and cache it.
- On by default; `LocaleConfig(localize_openapi=False)` turns it off.

## Consequences

- The schema and the docs pages follow the request locale with no extra endpoints (DOC-01 to DOC-05).
- Identical English text is translated the same way everywhere, unless the translator adds a
  translation under the `openapi` context for schema text.
- Descriptions written as docstrings stay in the source language; the user guide says to pass
  `description=gettext_noop(...)` instead.

## Related requirements

DOC-01 to DOC-05
