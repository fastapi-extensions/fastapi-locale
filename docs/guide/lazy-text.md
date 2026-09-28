# Lazy text

Text that is defined once and sent in many responses must be translated per response, not when the
module is imported. `gettext_lazy()` and its plural and context variants return a `LazyText`, which holds
the message and is translated each time it is rendered.

```python
from fastapi import HTTPException
from pydantic import BaseModel

from fastapi_locale import LazyText, gettext_lazy, ngettext_lazy

ITEM_NOT_FOUND = gettext_lazy("Item not found")


class Order(BaseModel):
    status: LazyText = gettext_lazy("Pending")


@app.get("/orders/{order_id}")
async def read_order(order_id: int) -> Order:
    if order_id not in orders:
        raise HTTPException(status_code=404, detail=ITEM_NOT_FOUND)
    return orders[order_id]
```

## Where it works

| Place | Rendered |
| --- | --- |
| Model field typed `LazyText` | When the response is serialized |
| `HTTPException.detail`, also nested in dicts and lists | By the library's HTTP exception handler |
| Values in a returned `dict` or `list` | When the response is serialized |
| `str(text)` or an f-string | Immediately, in the active locale |

In the OpenAPI schema a `LazyText` field is a plain string.

## Rules

- Type the field as `LazyText`. A `str` field rejects it, which Pydantic reports clearly.
- `model_dump()` keeps the `LazyText`; `model_dump_json()` and FastAPI responses render it.
- Two lazy texts are equal when their message and values are equal. A lazy text is never equal to a plain
  string, because that comparison would depend on the active locale. Call `str()` to compare text.
- `+`, `%` and slicing are not supported. Use placeholders instead:
  `gettext_lazy("Hello {name}", name=user.name)`.
- Lazy text can be pickled, for example to pass it to a task queue.

## Route and model documentation

Lazy text is for response data. For route summaries, descriptions and field descriptions use
`gettext_noop()`; the schema is translated separately. See [API documentation](api-documentation.md).
