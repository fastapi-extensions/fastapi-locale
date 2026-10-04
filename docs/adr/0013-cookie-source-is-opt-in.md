# ADR-0013: Leave the cookie source out of the default sources

- Status: Accepted
- Accepted: 2026-10-04
- Date: 2026-10-04

## Context

The default sources were the `lang` query parameter, a `locale` cookie and `Accept-Language`. A response
must name in `Vary` every request header that can change it (LOC-11), whether or not a given request sent
that header. With the cookie source in the defaults, every response of every application carried
`Vary: Cookie`, including applications that never set such a cookie. Many CDNs and shared caches treat
`Vary: Cookie` as uncacheable.

## Options considered

1. **Keep the cookie in the defaults.** Convenient for sites with a language switcher, but every API pays
   for it in cacheability without having asked for it.
2. **Default to the query parameter and `Accept-Language`; the cookie source is added by the application.**
   One line of configuration for those who want it.
3. **Add `Cookie` to `Vary` only when the request has the cookie.** Wrong: a response to a request without
   the cookie would be reused for a request with it.

## Decision

Use option 2. `LocaleConfig(sources=None)` means `QueryParamSource()` then `AcceptLanguageSource()`.
`CookieSource` stays a built-in source and is documented next to the caching guidance.

## Consequences

- Responses carry `Vary: Accept-Language` by default and remain cacheable per language.
- Applications that used the cookie through the defaults add `CookieSource()` to `sources`.
- LOC-04 still holds: the query parameter, cookie and header sources are all built in.

## Related requirements

LOC-03, LOC-04, LOC-11
