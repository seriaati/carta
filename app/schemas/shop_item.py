from pydantic import BaseModel

from app.core.enums import ShopItemType
from app.models.card import Card


class ShopItemResponse(BaseModel):
    id: int
    name: str
    price: int
    type: ShopItemType
    rate: float
    card_id: int | None
    card: Card | None = None
    created_at: str
    updated_at: str


class ShopItemUpdate(BaseModel):
    name: str | None = None
    price: int | None = None
    type: ShopItemType | None = None
    rate: float | None = None
    card_id: int | None = None
