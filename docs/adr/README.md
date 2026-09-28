# Architecture decision records

Each significant design decision is recorded here, one file per decision, using the format described in
[ADR-0001](0001-record-architecture-decisions.md). A record is never rewritten after it is accepted; a
later record supersedes it instead.

| ADR | Title | Status |
| --- | --- | --- |
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-gettext-catalogs-through-babel.md) | Use GNU gettext catalogs loaded through Babel | Accepted |
| [0003](0003-request-locale-in-a-context-variable.md) | Hold the request locale in a context variable with a per-request holder | Accepted |
| [0004](0004-middleware-resolves-dependencies-refine.md) | Resolve the locale in middleware and let dependencies refine it | Accepted |
| [0005](0005-lazy-text-type.md) | Lazy text as a dedicated Pydantic-aware type | Accepted |
| [0006](0006-validation-messages-keyed-on-error-type.md) | Key validation messages on the Pydantic error type | Accepted |
| [0007](0007-named-placeholder-formatting.md) | Named placeholder formatting instead of str.format | Accepted |
| [0008](0008-load-catalogs-at-setup.md) | Load catalogs when the application is set up | Accepted |
| [0009](0009-localized-openapi.md) | Localize OpenAPI by translating the generated schema | Accepted |
| [0010](0010-toolchain.md) | Project toolchain | Accepted |
