# ADR-0009: Localize OpenAPI by translating the generated schema

- Status: Proposed (to be confirmed by a prototype before DOC-01 is built)
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

## Decision

Option 3 is proposed. It uses FastAPI's public output rather than its internals, and it covers route
metadata, tags and model fields in one pass.

## Consequences

- The schema endpoint and the docs pages gain a locale parameter (DOC-01 to DOC-03).
- Identical English text is translated the same way everywhere in the schema. Context-specific text needs
  distinct wording.
- A prototype must confirm the approach against real applications before the work is scheduled.

## Related requirements

DOC-01, DOC-02, DOC-03
