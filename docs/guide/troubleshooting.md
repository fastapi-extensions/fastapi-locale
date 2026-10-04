# Troubleshooting

## Messages are not translated

Check, in order:

1. **Is the catalog compiled?** The application loads `.mo` files. Run `fastapi-locale compile` after
   editing a `.po` file, then restart.
2. **Is the entry fuzzy?** Fuzzy entries are not compiled. Remove the `#, fuzzy` flag after reviewing the
   translation. `fastapi-locale check` lists them.
3. **Is the locale supported?** It must be in `supported_locales`. Look at the `Content-Language` header
   of the response to see which locale was chosen.
4. **Does the msgid match exactly?** Placeholders, punctuation and spaces must match the code.
5. **Is the message in the right domain?** `dgettext("admin", ...)` reads `admin.mo`, not `messages.mo`.
6. **Did the startup log warn** "No 'messages' catalog found for supported locale ..."? Then the
   directory layout is not `<dir>/<locale>/LC_MESSAGES/messages.mo`.

## `CatalogLoadError` at startup

A directory in `catalog_dirs` does not exist, or a `.mo` file in it cannot be read. The message names the
path. An empty or cut-off `.mo` file usually means the compile step was interrupted; run
`fastapi-locale compile` again.

## `LocalizationNotConfiguredError`

Translation was called with no `Localization` set up, typically in a script or at import time. Create the
`Localization` first and call `install(app)` or `make_default()`, or use `gettext_lazy()` for text defined
at import time.

## `NoActiveRequestError`

`set_locale()` changes the current request's locale and was called where no request is being handled. For
a block of code outside a request, use `use_locale()`.

## Text is in the default language inside a thread

`loop.run_in_executor()` does not carry the request's locale. Use `asyncio.to_thread()` or pass the
context yourself; see [threads and tasks](translating.md#threads-and-tasks).

## `ValueError: ... was created in a different Context`

A `use_locale()` block was left in a different context than it was entered in, usually because it wraps a
`yield` in a sync dependency. Keep the block inside one function, or call `set_locale()` to change the
language of the whole request.

## Pydantic rejects lazy text

A field typed `str` does not accept `LazyText`. Type the field as `LazyText`.

## `Object of type LazyText is not JSON serializable`

The lazy text reached a JSON encoder that FastAPI does not control: a response you built yourself, or
the default exception handler of an application that has no `install()`. Render it with `str()`, or call
`install()` on [each mounted application](validation-errors.md#mounted-applications).

## Plural forms are wrong

The plural rule comes from the `Plural-Forms` header of the `.po` file. Catalogs created with
`fastapi-locale init` get the correct rule from CLDR. `fastapi-locale check` reports catalogs without the
header.

## A placeholder shows up literally, like `{name}`

The message uses a placeholder that got no value: the translation names one the code does not pass, or
the call passes no values at all. The log has a warning naming it, and `fastapi-locale check` reports a
translation with an unknown placeholder. For a literal brace, write `{{` and `}}`.

## Validation errors are in English for one field

Some Pydantic context values are English text produced by the parser, for example the detail in
`date_parsing` errors, or the list of choices in `literal_error`. Only the template around them is
translated.
