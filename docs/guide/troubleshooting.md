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
5. **Did the startup log warn** "No 'messages' catalog found for supported locale ..."? Then the
   directory layout is not `<dir>/<locale>/LC_MESSAGES/messages.mo`.

## `LocalizationNotConfiguredError`

Translation was called with no `Localization` set up, typically in a script or at import time. Create the
`Localization` first and call `install(app)` or `make_default()`, or use `gettext_lazy()` for text defined
at import time.

## `set_locale()` raises outside a request

`set_locale()` changes the current request's locale. For a block of code outside a request, use
`use_locale()`.

## Pydantic rejects lazy text

A field typed `str` does not accept `LazyText`. Type the field as `LazyText`.

## Plural forms are wrong

The plural rule comes from the `Plural-Forms` header of the `.po` file. Catalogs created with
`fastapi-locale init` get the correct rule from CLDR. `fastapi-locale check` reports catalogs without the
header.

## A placeholder shows up literally, like `{name}`

The translation uses a placeholder the code does not pass. The log has a warning naming it, and
`fastapi-locale check` reports it as an unknown placeholder.

## Validation errors are in English for one field

Some Pydantic context values are English text produced by the parser, for example the detail in
`date_parsing` errors, or the list of choices in `literal_error`. Only the template around them is
translated.
