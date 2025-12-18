from typing import TYPE_CHECKING, Optional

import sqlmodel
from sqlalchemy.orm import Mapped

from app.core.enums import CardRarity

from ._base import BaseModel

if TYPE_CHECKING:
    from app.models.shop_item import ShopItem


class Card(BaseModel, table=True):
    __tablename__: str = "cards"

    id: int = sqlmodel.Field(primary_key=True, index=True, default=None)
    name: str = sqlmodel.Field(max_length=100, index=True)
    image_url: str
    description: str
    rarity: CardRarity

    attack: int | None
    defense: int | None
    price: int

    shop_item: Mapped[Optional["ShopItem"]] = sqlmodel.Relationship(back_populates="card")

    def __str__(self) -> str:
        return f"{self.name} (#{self.id})"
