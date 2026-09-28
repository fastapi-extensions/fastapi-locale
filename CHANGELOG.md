# Changelog

All notable changes are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[semantic versioning](https://semver.org).

## [Unreleased]

## [0.1.0rc1] - 2026-09-28

First release candidate. Installs only with `pip install --pre fastapi-locale` or an exact version.

### Added

- Per-request locale from query parameter, cookie and `Accept-Language`, with RFC 4647 matching and
  `Content-Language` and `Vary` response headers.
- gettext, ngettext, pgettext, npgettext and their domain variants, with named placeholders.
- `LazyText` for translatable text in Pydantic models, response models and `HTTPException.detail`.
- Localized 422 validation errors for every Pydantic error type, with built-in German, Spanish, French,
  Hindi and Portuguese (Brazil) translations.
- `set_locale()` to apply a signed-in user's language for the rest of a request.
- `LocaleDep` and `TranslatorDep` dependencies, `use_locale()`, and test helpers.
- `fastapi-locale` command: extract, init, update, compile and check.
- Localized OpenAPI schema: Swagger UI and ReDoc follow the request locale, with built-in
  translations of FastAPI's own schema text. Turn off with `localize_openapi=False`.
