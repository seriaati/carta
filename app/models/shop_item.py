from typing import TYPE_CHECKING, Optional

import sqlmodel
from sqlalchemy.orm import Mapped

from app.core.enums import ShopItemType

from ._base import BaseModel

if TYPE_CHECKING:
    from app.models.card import Card
    from app.models.inventory import Inventory


class ShopItem(BaseModel, table=True):
    __tablename__: str = "shop_items"

    id: int = sqlmodel.Field(primary_key=True, index=True, default=None)
    name: str = sqlmodel.Field(max_length=100, index=True)
    price: int
    type: ShopItemType
    rate: float = sqlmodel.Field(default=1.0)

    card_id: int | None = sqlmodel.Field(foreign_key="cards.id", index=True, nullable=True)

    inventories: list["Inventory"] = sqlmodel.Relationship(back_populates="item")

    card: Mapped[Optional["Card"]] = sqlmodel.Relationship(
        back_populates="shop_item", sa_relationship_kwargs={"uselist": False}
    )
