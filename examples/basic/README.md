# Example: inventory API

A small API that uses fastapi-locale for translated responses, lazy text, localized validation errors
and the user's saved language.

```sh
cd examples/basic
uv run fastapi-locale compile
uv run uvicorn app:app --reload
```

Then try:

```sh
curl -H "Accept-Language: de" http://127.0.0.1:8000/
curl -H "Accept-Language: hi" http://127.0.0.1:8000/items/9
curl -H "Accept-Language: de" -H "Content-Type: application/json" \
     -d '{"name": "ab", "quantity": 0}' http://127.0.0.1:8000/items
curl -H "X-User-Language: hi" -H "Content-Type: application/json" \
     -d '{"name": "Milk", "quantity": 3}' http://127.0.0.1:8000/items
```
