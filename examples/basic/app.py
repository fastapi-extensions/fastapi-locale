"""A small inventory API showing the main features of fastapi-locale.

Run it with:  fastapi-locale compile  &&  uvicorn app:app --reload   (from this directory)
"""

from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from fastapi_locale import (
    LazyText,
    LocaleConfig,
    LocaleDep,
    Localization,
    TranslatorDep,
    UnsupportedLocaleError,
    gettext_lazy,
    gettext_noop,
    set_locale,
)

i18n = Localization(
    LocaleConfig(
        default_locale="en",
        supported_locales=["en", "de", "hi"],
        catalog_dirs=[Path(__file__).parent / "locales"],
    )
)
app = FastAPI(
    title=gettext_noop("Inventory"),
    description=gettext_noop("A small inventory API that answers in your language."),
)
i18n.install(app)

ITEM_NOT_FOUND = gettext_lazy("Item not found")
ITEMS: dict[int, str] = {1: "Coffee", 2: "Tea"}


class NewItem(BaseModel):
    name: str = Field(min_length=3, description=gettext_noop("Display name of the item"))
    quantity: int = Field(gt=0)


class Item(BaseModel):
    id: int
    name: str
    status: LazyText = gettext_lazy("In stock")
    summary: str = ""


async def current_user(x_user_language: Annotated[str | None, Header()] = None) -> None:
    """Stand-in for real authentication: apply the user's saved language."""
    if x_user_language:
        with suppress(UnsupportedLocaleError):
            set_locale(x_user_language)


@app.get("/")
async def welcome(tr: TranslatorDep, locale: LocaleDep) -> dict[str, str]:
    return {"message": tr.gettext("Welcome to the inventory"), "locale": locale.tag}


@app.get("/items/{item_id}", summary=gettext_noop("Read an item"))
async def read_item(item_id: int) -> Item:
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail=ITEM_NOT_FOUND)
    return Item(id=item_id, name=ITEMS[item_id])


@app.post("/items", status_code=201, dependencies=[Depends(current_user)])
async def create_item(item: NewItem, tr: TranslatorDep) -> Item:
    item_id = max(ITEMS) + 1
    ITEMS[item_id] = item.name
    summary = tr.ngettext(
        "{n} unit of {name} added", "{n} units of {name} added", item.quantity, name=item.name
    )
    return Item(id=item_id, name=item.name, summary=summary)
