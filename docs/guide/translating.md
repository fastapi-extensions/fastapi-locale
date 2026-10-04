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

`n` must be an integer. Anything else raises `TypeError`, in every locale.

## Placeholders

Use named placeholders so translators can move them:

```python
gettext("{count} new messages for {name}", count=3, name="Asha")
```

In plural functions, `n` is available as `{n}`. Only `{name}` is substituted; attribute access such as
`{user.email}` is left as written, so a translation can never read data it was not given.

Write `{{` and `}}` for literal braces. This holds whether or not the call passes values. A placeholder
that gets no value is left as written and logged once as a warning.

## Text defined at import time

Module-level constants, default values of model fields and shared error messages are created before any
request exists. Use [lazy text](lazy-text.md) for them.

## Another locale for a block

```python
from fastapi_locale import use_locale

with use_locale(user.language):
    send_email(subject=gettext("Your order has shipped"))
```

This does not change the language of the current response. The block yields the matched locale, so
`with use_locale("hi-IN") as locale` gives `hi` when only `hi` is supported.

Keep the block inside one function. Do not wrap a `yield` in it, for example in a dependency: FastAPI may
run the two halves in different contexts. To change the language of the whole request, call
[`set_locale()`](user-language.md).

## Threads and tasks

The active locale follows the request into `async` code, sync routes and dependencies, background tasks,
`asyncio.create_task()` and `asyncio.to_thread()`.

`loop.run_in_executor()` does not carry it, because it does not copy context variables. Code started that
way sees the default locale. Use `asyncio.to_thread()`, or pass the context yourself:

```python
import contextvars

context = contextvars.copy_context()
await loop.run_in_executor(None, context.run, render_report)
```

## Domains

Each `.mo` file name is a domain: `messages.mo` is the default, `admin.mo` is the `admin` domain. The
library's own messages live in the `fastapi_locale` domain. The command line tool keeps one template and
one catalog per domain; see [command line tool](command-line.md#domains).
