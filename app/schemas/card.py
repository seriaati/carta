from pydantic import BaseModel

from app.core.enums import CardRarity, CardSortField, SortOrder


class CardListParams(BaseModel):
    """Query parameters for listing cards."""

    search_name: str | None = None
    search_id: int | None = None
    sort_by: CardSortField = CardSortField.ID
    sort_order: SortOrder = SortOrder.ASC


class CardCreate(BaseModel):
    name: str
    image: str  # Frontend sends base64 data URI (e.g., 'data:image/png;base64,...')
    description: str
    rarity: CardRarity
    attack: int | None = None
    defense: int | None = None
    price: int


class CardUpdate(BaseModel):
    name: str | None = None
    image: str | None = None  # Frontend sends base64 data URI (e.g., 'data:image/png;base64,...')
    description: str | None = None
    rarity: CardRarity | None = None
    attack: int | None = None
    defense: int | None = None
    price: int | None = None
