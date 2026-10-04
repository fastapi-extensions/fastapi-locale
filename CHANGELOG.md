# Changelog

All notable changes are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[semantic versioning](https://semver.org).

## [Unreleased]

## [0.1.0rc2] - 2026-10-04

Second release candidate. The public API is now defined and pinned: see "What is public" in the API
reference. Several names changed since 0.1.0rc1 to make it consistent; they are listed under "Changed"
and "Removed".

### Added

- `RequestLocale`, the documented type of `request.state.locale`, with `locale` and `decided_by`.
  `set_locale()` is recorded in `decided_by`.
- Lazy variants for other domains: `dgettext_lazy`, `dngettext_lazy`, `dpgettext_lazy` and
  `dnpgettext_lazy`.
- `NoActiveRequestError`.
- `fastapi_locale.__version__` and `fastapi-locale --version`.
- A request for `pt` or `pt-PT` uses `pt-BR` when no closer locale is supported, and likewise for other
  languages. The built-in Portuguese messages serve `pt` and `pt-PT`.
- Command line tool: one template and one catalog per domain, `compile` builds every domain, and an
  `exclude` setting. Virtual environments, `node_modules` and `site-packages` are never scanned.
- The OpenAPI schema translates the summaries and descriptions of named examples and OAuth scope
  descriptions.
- The pytest plugin restores the default localization after each test, and the `locale` marker accepts
  `tag=`.

### Changed

- The default sources are the `lang` query parameter and `Accept-Language`. To read a cookie, add
  `CookieSource()` to `sources`. Responses no longer carry `Vary: Cookie` unless you do.
- `CookieSource(name=...)` is now `CookieSource(cookie=...)`.
- `LocaleConfig(builtin_error_messages=...)` is now `builtin_catalogs`.
- `use_locale()` yields the matched `Locale` instead of a `Translator`.
- `set_locale()` outside a request raises `NoActiveRequestError`.
- A missing catalog directory raises `CatalogLoadError` when the `Localization` is created. `LocaleConfig`
  no longer reads the filesystem, and rejects a single string or path where a list is expected.
- `install()` always makes its localization the default for code outside requests.
- `{{` and `}}` are literal braces in every translation call, with or without values.
- The plural functions require an integer `n` in every locale.
- Validation messages keep Pydantic's own text when no translation exists, so responses in the source
  language are identical to FastAPI's.
- A locale source is any callable; `name` and `vary` are optional attributes.
- Command line settings: `locales_dir` is now `catalog_dir` and `domain` is now `default_domain`. Unknown
  settings and source directories that do not exist are errors.

### Removed

- `Localization.store`, `resolve()`, `vary`, `default_locale` and `supported_locales`, `Resolution`,
  `LocaleConfig.locales`, `Translator.translate()` and `Locale.truncations()`. They exposed internals; use
  `Localization.config`, `Localization.translator()` and `request.state.locale` instead.
- The `locales` setting of the command line tool, which had no effect.

### Fixed

- A locale in the source language no longer falls back to the default locale's catalog. With a default
  locale other than the source language, English requests were answered in the default language.
- `set_locale(None)` raises `UnsupportedLocaleError` like any other unsupported value.
- A locale source that returns something other than language tags is skipped instead of failing the
  request.
- An empty, cut-off or wrongly encoded `.mo` file raises `CatalogLoadError` with the file name.
- Request values that cannot be language tags are no longer kept in the match cache.
- OpenAPI: a lazy default value is rendered in the default locale for every reader, the translated schema
  follows FastAPI when it rebuilds the schema, data under `x-` extension keys is left alone, and fields or
  responses named `default`, `example`, `enum` or `const` are translated.
- Validation messages write numbers as Pydantic does, handle an unknown length, and never show a raw
  placeholder when an error lacks a value.
- Every `Vary` line of a response is kept when the library adds its own headers.
- `install()` on an application that has already started changes nothing instead of leaving it half set
  up.
- A mounted application with the same localization installed shares the request's locale.
- `gettext()` finds a message that the catalog stores with plural forms.
- Command line tool: `dgettext()` messages are no longer written to the default domain's template, and
  `extract` leaves an unchanged template alone.

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
