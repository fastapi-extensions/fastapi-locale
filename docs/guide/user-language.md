# The user's saved language

Signed-in users often choose a language in their profile. That choice should win over the browser's
`Accept-Language`, for the whole request.

Call `set_locale()` where you load the user:

```python
from contextlib import suppress
from typing import Annotated

from fastapi import Depends

from fastapi_locale import UnsupportedLocaleError, set_locale


async def current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    user = await users.get_by_token(token)
    with suppress(UnsupportedLocaleError):
        set_locale(user.language)
    return user
```

From that point on, the request uses the user's language:

- route code, `TranslatorDep` and `LocaleDep`
- lazy text in the response
- validation errors
- the `Content-Language` header

## Why validation errors follow too

FastAPI runs a route's dependencies before it validates the request body. The locale lives in one
holder per request, and `set_locale()` changes that holder, so the validation error handler sees the new
locale.

One case cannot work: if a parameter of `current_user` itself is invalid, FastAPI never calls it, and the
errors use the locale from the request.

## Matching

`set_locale("hi-IN")` uses `hi` when only `hi` is supported, the same
[matching](locale-resolution.md#matching) as for requests. If nothing matches it raises
`UnsupportedLocaleError`, which the example above ignores. A user with no saved language is covered too:
`None` and an empty string count as unsupported.

## Outside requests

`set_locale()` only works during a request; elsewhere it raises `NoActiveRequestError`. For a block of
code, for example an email in the recipient's language, use `use_locale()`. It does not change the current
response.
