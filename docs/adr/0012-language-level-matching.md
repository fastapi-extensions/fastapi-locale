# ADR-0012: Match another region of the language when lookup finds nothing

- Status: Accepted
- Accepted: 2026-10-04
- Date: 2026-10-04

## Context

RFC 4647 lookup only shortens the requested tag: `hi-IN` reaches `hi`. It never reaches a longer or a
sibling tag. An application that supports `pt-BR` therefore answered a request for `pt` or `pt-PT` in its
default locale, usually English, although it had Portuguese text. The same happened for `zh` against
`zh-Hans` and for `en-GB` against `en-US`. Browsers of users outside the supported region send exactly
such values.

The built-in error catalogs had the same gap: the Portuguese one is `pt_BR`, so an application that
configured `pt` got English validation messages.

## Options considered

1. **Lookup only.** Predictable and standard, but serves the wrong language in common cases.
2. **Lookup, then any supported locale in the same language.** What Django does. Simple to explain and to
   test.
3. **CLDR likely-subtag matching.** Scores candidates by language distance. More precise for scripts and
   macro-languages, but harder to predict and it needs CLDR data on the request path.

## Decision

Use option 2.

- A candidate is matched with RFC 4647 lookup first. If no tag in its chain is supported, the first
  supported locale with the same language subtag is used, in the order of `supported_locales`.
- A script named in the request is never crossed: `zh-Hant-TW` does not match `zh-Hans`. A request without
  a script matches any script.
- Candidates are still tried one by one in order of preference, so `pt-PT, en;q=0.8` prefers `pt-BR` over
  `en`.
- `set_locale()`, `use_locale()` and `Localization.translator()` use the same matching.
- A built-in regional catalog also serves its bare language when no catalog ships for that language.

## Consequences

- A reader gets their language whenever the application has it in any region.
- `Content-Language` names the locale that was served, which may be another region than the one requested.
- An application that supports several regions of a language decides the fallback by their order in
  `supported_locales`.
- Application catalogs are not shared between regions. A message missing in `pt-PT` still falls back to
  `pt` and then to the default locale.

## Related requirements

LOC-02, LOC-08, ERR-10
