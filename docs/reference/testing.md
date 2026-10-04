# Pytest plugin

::: fastapi_locale.testing
    options:
      members: false

To force the locale of requests in a test, use
[`Localization.override()`](setup.md#fastapi_locale.Localization.override). To replace what a route
receives, override the [dependencies](dependencies.md) `current_locale` and `current_translator`.
The [testing guide](../guide/testing.md) has examples.
