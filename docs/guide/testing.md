# Testing

## Force a locale for requests

```python
def test_german_welcome(client: TestClient) -> None:
    with i18n.override("de"):
        assert client.get("/").json()["message"] == "Willkommen"
```

Every request in the block uses `de`, whatever headers it sends.

## Code called directly

```python
from fastapi_locale import use_locale

with use_locale("hi"):
    assert format_invoice(order).startswith("चालान")
```

## The pytest plugin

Enable the plugin in `conftest.py`:

```python
pytest_plugins = ["fastapi_locale.testing"]
```

It adds the `locale` marker, which runs the test body as `use_locale()` would:

```python
@pytest.mark.locale("fr")
def test_invoice_in_french() -> None: ...
```

The marker needs a `Localization` that is installed or made default at import time, because it runs
before the test's own fixtures.

The plugin also puts back, after each test, the localization that code outside requests used before the
test. A test that builds its own application and installs a `Localization` does not affect the next one.

## Replace the dependencies

```python
from fastapi_locale import current_translator

app.dependency_overrides[current_translator] = lambda: i18n.translator("de")
```
