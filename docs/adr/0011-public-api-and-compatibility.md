# ADR-0011: Define the public API as the names exported by the package

- Status: Accepted
- Accepted: 2026-10-04
- Date: 2026-10-04

## Context

A stable release is a promise about what applications can rely on. Before this record the project had no
written rule. Every public name could be imported two ways (`fastapi_locale.LazyText` and
`fastapi_locale.lazy.LazyText`), the leading underscore of a module marked its layer rather than its
visibility, and public objects handed out internal ones: `Localization.store` returned the catalog store,
and `request.state.locale` was an undocumented mutable holder.

## Options considered

1. **Everything without a leading underscore is public.** No work, but it freezes helper functions and
   internal classes that were never meant for applications.
2. **Only the names exported by `fastapi_locale` are public.** One import path, one list to review, and
   the list can be pinned by a test.
3. **Rename every internal module with an underscore.** Makes the rule visible in the file tree, at the
   cost of renaming most of the package.

## Decision

Use option 2.

- The public API is `fastapi_locale.__all__`, the pytest plugin `fastapi_locale.testing`, the
  `fastapi-locale` command with its settings, and what the library adds to an application:
  `request.state.locale`, `app.state.localization`, the `Content-Language` and `Vary` headers, the
  `fastapi_locale` logger, and the domain and contexts of the built-in catalogs.
- A module without a leading underscore exports public names only. Modules that hold only internal names
  are underscored.
- A public object exposes only public types. The catalog store, negotiation and the `Vary` list are
  internal to `Localization`. `RequestLocale` is public, with two read-only properties.
- A unit test compares `fastapi_locale.__all__` with the documented list, so a change to the public API
  is always a deliberate edit.
- The project follows semantic versioning. An incompatible change raises the major version, or the minor
  version before 1.0. Where it is possible, the old form keeps working for one minor release with a
  `DeprecationWarning`.

## Consequences

- Applications import from `fastapi_locale` and can ignore the module layout, which stays free to change.
- Translators are obtained, not constructed, so the catalog classes stay internal.
- The reference documentation can be checked against one list.
- Internal helpers are still importable, as everything in Python is. The rule is stated in the reference so
  that doing so is a known risk.

## Related requirements

C-05, NFR-13, NFR-15
