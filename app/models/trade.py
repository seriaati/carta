from typing import TYPE_CHECKING, Optional

import sqlmodel
from sqlalchemy.orm import Mapped

from app.core.enums import TradeStatus

from ._base import BaseModel

if TYPE_CHECKING:
    from .card import Card


class Trade(BaseModel, table=True):
    __tablename__: str = "trades"
    __table_args__ = (
        sqlmodel.CheckConstraint(
            "(requested_card_id IS NOT NULL) OR (price IS NOT NULL)",
            name="requested_card_or_price_not_null",
        ),
    )

    id: int = sqlmodel.Field(primary_key=True, index=True, default=None)
    proposer_id: int = sqlmodel.Field(
        foreign_key="players.id", index=True, sa_type=sqlmodel.BigInteger
    )
    receiver_id: int = sqlmodel.Field(
        foreign_key="players.id", index=True, sa_type=sqlmodel.BigInteger
    )
    offered_card_id: int = sqlmodel.Field(foreign_key="cards.id", index=True)
    requested_card_id: int | None = sqlmodel.Field(
        foreign_key="cards.id", index=True, nullable=True, default=None
    )
    price: int | None = None
    status: TradeStatus = TradeStatus.PENDING

    offered_card: Mapped["Card"] = sqlmodel.Relationship(
        sa_relationship_kwargs={"lazy": "joined", "foreign_keys": "[Trade.offered_card_id]"}
    )
    requested_card: Mapped[Optional["Card"]] = sqlmodel.Relationship(
        sa_relationship_kwargs={"lazy": "joined", "foreign_keys": "[Trade.requested_card_id]"}
    )
