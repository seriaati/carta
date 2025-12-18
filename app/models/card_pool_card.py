import sqlmodel

from ._base import BaseModel


class CardPoolCard(BaseModel, table=True):
    __tablename__: str = "card_pool_cards"

    id: int = sqlmodel.Field(primary_key=True, index=True, default=None)
    pool_id: int = sqlmodel.Field(foreign_key="card_pools.id", index=True)
    card_id: int = sqlmodel.Field(foreign_key="cards.id", index=True)
    probability: float = sqlmodel.Field(default=0.0, ge=0.0, le=1.0)
