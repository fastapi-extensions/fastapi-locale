#!/usr/bin/env bash
# Check built distributions in dist/ before they are published:
#   1. metadata and README render the way PyPI will show them,
#   2. the wheel contains the type marker and the built-in catalogs and no build output,
#   3. the wheel installs into a clean environment and works.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
shopt -s nullglob
wheels=(dist/*.whl)
sdists=(dist/*.tar.gz)
if [[ ${#wheels[@]} -ne 1 || ${#sdists[@]} -ne 1 ]]; then
  echo "expected exactly one wheel and one sdist in dist/" >&2
  exit 1
fi
wheel="${wheels[0]}"

echo "==> Metadata"
uvx --quiet twine check --strict dist/*

echo "==> Wheel contents"
contents="$(python3 -m zipfile -l "$wheel")"
for required in "fastapi_locale/py.typed" \
  "fastapi_locale/locales/fastapi_locale.pot" \
  "fastapi_locale/locales/de/LC_MESSAGES/fastapi_locale.po"; do
  grep -q "$required" <<< "$contents" || { echo "missing from wheel: $required" >&2; exit 1; }
done
if grep -qE "\.mo$|/tests/|__pycache__" <<< "$contents"; then
  echo "wheel contains build output or tests" >&2
  exit 1
fi

echo "==> Clean install"
venv="$(mktemp -d)/venv"
uv venv --quiet "$venv"
uv pip install --quiet --python "$venv/bin/python" "$wheel" httpx2
"$venv/bin/fastapi-locale" --help > /dev/null
"$venv/bin/python" - << 'PY'
import warnings

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from fastapi_locale import LocaleConfig, Localization

warnings.simplefilter("ignore", DeprecationWarning)
app = FastAPI()
Localization(LocaleConfig(default_locale="en", supported_locales=["en", "de"])).install(app)


class Item(BaseModel):
    price: int = Field(gt=0)


@app.post("/")
def create(item: Item) -> Item:
    return item


response = TestClient(app).post("/", json={"price": 0}, headers={"Accept-Language": "de"})
assert response.status_code == 422, response.status_code
assert response.json()["detail"][0]["msg"] == "Eingabe muss größer als 0 sein", response.json()
assert response.headers["content-language"] == "de"
print("installed wheel works")
PY
echo "==> All distribution checks passed"
