# API reference

## What is public

The public API is every name you can import from the top-level package:

```python
from fastapi_locale import LocaleConfig, Localization, gettext
```

together with:

- the pytest plugin `fastapi_locale.testing`;
- the `fastapi-locale` command, its options and its settings in `pyproject.toml`;
- what the library adds to an application: `request.state.locale`, `app.state.localization`, the
  `Content-Language` and `Vary` response headers, and the `fastapi_locale` logger;
- the built-in catalogs' domain, `fastapi_locale`, and its message contexts (the Pydantic error types
  and `openapi`), which applications use to override a message.

Everything else is internal and may change in any release. That covers names that start with an
underscore, and importing from a submodule such as `fastapi_locale.lazy` instead of from `fastapi_locale`.

## Compatibility

fastapi-locale follows [semantic versioning](https://semver.org). A change that breaks the public API
raises the major version; before 1.0 it raises the minor version. Every such change is listed in the
[changelog](../about/changelog.md) under "Changed" or "Removed".

When something is replaced, the old form keeps working for at least one minor release and emits a
`DeprecationWarning` that names the replacement.

The wording of the built-in translations is not part of the API. It can be corrected in any release.

## Pages

| Page | Contents |
| --- | --- |
| [Setup](setup.md) | `Localization`, `LocaleConfig`, the middleware and OpenAPI localization |
| [Translation](translation.md) | `gettext()` and the other translation functions, `Translator` |
| [Locale context](context.md) | The active locale: reading it, changing it, `Locale`, `RequestLocale` |
| [Lazy text](lazy.md) | `LazyText` and the `*_lazy` functions |
| [Dependencies](dependencies.md) | `LocaleDep`, `TranslatorDep` |
| [Locale sources](sources.md) | Where a request's locale comes from |
| [Errors and exceptions](errors.md) | Exception handlers and the exceptions the library raises |
| [Testing](testing.md) | The pytest plugin |
