# ADR-0002: Use GNU gettext catalogs loaded through Babel

- Status: Accepted
- Accepted: 2026-09-28
- Date: 2026-09-26

## Context

Translations need a storage format that translators already know, that handles plural forms correctly for
every language, and that has tooling for extracting messages from Python code.

## Options considered

1. **GNU gettext (`.po` / `.mo`) read with Babel.** The standard in Python (Django, Flask-Babel, CPython
   itself). Supported by Poedit, Weblate, Crowdin, Transifex and Lokalise. Babel adds CLDR plural rules,
   message extraction and compilation.
2. **gettext through the standard library only.** No extra dependency, but no extraction tooling, no CLDR
   data and no locale formatting later.
3. **JSON or YAML catalogs.** Easy to read, but every project invents its own plural and context
   conventions, and the translation tools support them unevenly.
4. **Fluent (Project Fluent).** Expressive, but little adoption in the Python web world and a heavier
   runtime.

## Decision

Use option 1. Catalogs are `.po` files in the repository, compiled to `.mo` for runtime. Babel is a
runtime dependency, used for loading `.mo` files and plural rules, and the CLI builds on Babel's
extraction and compilation.

## Consequences

- Translators can use the tools they already have (C-01).
- Plural rules come from CLDR through each catalog's `Plural-Forms` header (TRN-02).
- Babel becomes a required dependency. It is mature and widely used, so the risk is low.
- JSON catalogs can still be added later behind the same catalog store interface, as the SRS notes.

## Related requirements

C-01, C-04, CAT-01, CAT-02, TRN-02, CLI-01, CLI-02
