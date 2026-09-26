# ADR-0005: Lazy text as a dedicated Pydantic-aware type

- Status: Proposed
- Date: 2026-09-26

## Context

Text defined at import time (default field values, shared error messages) must be translated later, in
the locale of the request that sends it. Django calls this `gettext_lazy`.

Experiments with FastAPI 0.141.1 and Pydantic 2.13.5 (see [Existing libraries](../research/existing-libraries.md),
section 6) showed that Babel's `LazyProxy`, which starlette-babel and starlette-i18n use, fails as
`HTTPException.detail`, in a response model, inside a returned dict, and in OpenAPI generation.

## Options considered

1. **Babel `LazyProxy`.** Fails in every FastAPI path tested. Rejected.
2. **A `str` subclass** holding the msgid and overriding `__str__`. JSON encoders read the underlying
   string, so `json.dumps` writes the msgid, untranslated. Rejected.
3. **A dedicated class with Pydantic core schema hooks.** Serializes through a plain serializer that calls
   `str()`, which translates in the active locale. Tested: works as a model field typed with the class, and
   shows in OpenAPI as `{"type": "string"}`.
4. **No lazy text**; translate eagerly everywhere. Simple, but import-time text cannot be localized.

## Decision

Use option 3, a final class `LazyText`:

- Created by `gettext_lazy`, `ngettext_lazy`, `pgettext_lazy` and `npgettext_lazy`.
- `str()` and `format()` translate in the active locale.
- Pydantic validation accepts `LazyText` or `str`; JSON serialization always produces a string. Python-mode
  `model_dump()` keeps the `LazyText`, so it can be rendered later.
- JSON schema is `{"type": "string"}`.
- Registered in `fastapi.encoders.ENCODERS_BY_TYPE` so `jsonable_encoder` renders it.
- Carries a `__pydantic_serializer__`, so Pydantic also renders it where the declared type is `Any` or
  `object`. FastAPI 0.141 serializes a route annotated `-> dict[str, object]` with Pydantic directly,
  without `jsonable_encoder`, which an integration test found.
- The library's HTTP exception handler renders `detail` through `jsonable_encoder`, because FastAPI's
  default handler passes `detail` straight to `json.dumps`.
- Equal when message, plural, context, domain and parameters are equal; hash on message, plural, context
  and domain. Not equal to a plain `str`, because that comparison would depend on the active locale.
- Supports pickling, so it can be passed to task queues.

## Consequences

- Works in response models, `HTTPException.detail` and plain dict responses (LZY-01 to LZY-05).
- Model fields that hold lazy text must be typed `LazyText`, not `str`. Pydantic's error makes the mistake
  obvious, and the user guide covers it.
- `ENCODERS_BY_TYPE` is not documented FastAPI API. A test fails if FastAPI changes it, so the break is
  caught in CI before a release.
- Lazy text in OpenAPI metadata is handled separately (ADR-0009).

## Related requirements

LZY-01 to LZY-06, ERR-09
