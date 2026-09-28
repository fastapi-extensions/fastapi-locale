# Translating messages

## Functions

All functions translate in the active locale: the request's locale, a `use_locale()` block, or the
default locale outside requests.

| Function | Use |
| --- | --- |
| `gettext(message, **params)` | A plain message. |
| `ngettext(singular, plural, n, **params)` | A message with plural forms, chosen by `n`. |
| `pgettext(context, message, **params)` | The same text with different meanings, such as "May" the month. |
| `npgettext(context, singular, plural, n, **params)` | Both of the above. |
| `dgettext`, `dngettext`, `dpgettext`, `dnpgettext` | The same, from another domain (catalog file). |

The same methods exist on `Translator`, which `TranslatorDep` injects into route handlers.

## Placeholders

Use named placeholders so translators can move them:

```python
gettext("{count} new messages for {name}", count=3, name="Asha")
```

In plural functions, `n` is available as `{n}`. Only `{name}` is substituted; attribute access such as
`{user.email}` is left as written, so a translation can never read data it was not given. Write `{{` and
`}}` for literal braces.

## Text defined at import time

Module-level constants, default values of model fields and shared error messages are created before any
request exists. Use [lazy text](lazy-text.md) for them.

## Another locale for a block

```python
from fastapi_locale import use_locale

with use_locale(user.language):
    send_email(subject=gettext("Your order has shipped"))
```

This does not change the language of the current response.

## Domains

Each `.mo` file name is a domain: `messages.mo` is the default, `admin.mo` is the `admin` domain. The
library's own error messages live in the `fastapi_locale` domain.
