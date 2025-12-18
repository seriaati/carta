from typing import TYPE_CHECKING

import sqlmodel

from ._base import BaseModel

if TYPE_CHECKING:
    from app.models.card import Card
    from app.models.shop_item import ShopItem


class Inventory(BaseModel, table=True):
    __tablename__: str = "inventories"
    __table_args__ = (
        sqlmodel.CheckConstraint(
            "(item_id IS NOT NULL) OR (card_id IS NOT NULL)", name="item_or_card_not_null"
        ),
    )

    id: int = sqlmodel.Field(primary_key=True, index=True, default=None)
    player_id: int = sqlmodel.Field(
        foreign_key="players.id", index=True, sa_type=sqlmodel.BigInteger
    )
    item_id: int | None = sqlmodel.Field(
        foreign_key="shop_items.id", index=True, nullable=True, default=None
    )
    card_id: int | None = sqlmodel.Field(
        foreign_key="cards.id", index=True, nullable=True, default=None
    )
    quantity: int = sqlmodel.Field(default=0, ge=0)

    item: "ShopItem" = sqlmodel.Relationship(back_populates="inventories")
    card: "Card" = sqlmodel.Relationship()
