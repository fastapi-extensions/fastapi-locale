# ADR-0006: Key validation messages on the Pydantic error type

- Status: Proposed
- Date: 2026-09-26

## Context

FastAPI's 422 responses carry Pydantic's English `msg`. pydantic-core 2.46.5 defines 104 error types; 47
have values in `ctx` such as `gt` or `min_length`. Some English messages build plurals inside `ctx`
(`string_too_short` uses `{expected_plural}`), which is wrong for most other languages.

pydantic-i18n, the only existing package in this area, matches the rendered English `msg` with a regular
expression. That breaks silently when Pydantic changes its wording.

## Options considered

1. **Match the English `msg` text.** Fragile across Pydantic releases. Rejected.
2. **Use Pydantic's own templates as msgids.** Ties catalogs to Pydantic's wording, which changes, and
   keeps the English plural logic.
3. **Library-owned templates keyed on `type`.** The library keeps one English template per error type,
   with named placeholders that match `ctx` keys, and uses the type as the gettext message context.

## Decision

Use option 3.

- Templates live in the library's own gettext domain, `fastapi_locale`, with `msgctxt` set to the error
  type.
- Types whose message depends on a number have a plural template and name the `ctx` key that picks the
  form (for example `min_length`). English-only `ctx` keys such as `expected_plural` are ignored.
- The built-in catalog directory is loaded first. An application overrides any message by shipping its own
  `fastapi_locale` catalog in its catalog directories, because later directories win (CAT-04).
- An error type with no template keeps Pydantic's `msg`.
- For `value_error` and `assertion_error`, only the fixed prefix is translated. The rest of the message is
  what the application raised, which it can translate with `gettext()` because validation runs inside the
  request.

## Consequences

- Catalogs no longer depend on Pydantic's wording (A-02).
- Plurals follow the target language's rules (ERR-04).
- The library must follow new error types in pydantic-core. A test lists all error types of the installed
  pydantic-core and fails when one has no template (NFR-09). It uses `list_all_errors`, which is not public
  Pydantic API, so it runs only in the test suite.
- Known limit: some `ctx` values are already English, for example `literal_error` renders `expected` as
  `'a' or 'b'`. Those values are passed through as they are.

## Related requirements

ERR-01 to ERR-08, NFR-09
