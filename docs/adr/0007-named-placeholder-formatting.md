# ADR-0007: Named placeholder formatting instead of str.format

- Status: Accepted
- Accepted: 2026-09-28
- Date: 2026-09-26

## Context

Translated messages contain values such as a name or a count. Translators must be able to move them,
because word order differs between languages. Catalogs are often edited by outside contributors, so a
translated string must not be able to run code or read arbitrary data.

## Options considered

1. **`str.format(**params)`.** A translated string like `{user.__class__}` or `{items[0]}` can read
   attributes and items of the arguments. Rejected for security (NFR-05).
2. **`%` formatting (`%(name)s`).** Safe from attribute access, but a translation with a missing key raises
   `KeyError`, and the `%` syntax is easy to break when editing.
3. **Own substitution of `{name}` only.** A small regular expression replaces `{identifier}` with the
   string form of the named value. `{{` and `}}` produce literal braces. Anything else is left as written.

## Decision

Use option 3. The same syntax is used for application messages and validation error templates, and it
matches the `{gt}` style of Pydantic's `ctx` keys.

If a translation names a placeholder that has no value, the placeholder is left as written and a warning
is logged once per message and locale. The request never fails because of it (NFR-06).

`fastapi-locale check` reports translations whose placeholders differ from the msgid, so these mistakes
are caught in CI before they reach production.

## Consequences

- Translators can reorder values freely (TRN-03).
- Translated strings cannot read attributes or items.
- Format specifications such as `{price:.2f}` are not supported. Numbers that need locale formatting will
  use the formatting helpers planned in FMT-02.

## Related requirements

TRN-03, NFR-05, NFR-06, CLI-04
