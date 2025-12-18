import sqlmodel

from ._base import BaseModel


class CardPool(BaseModel, table=True):
    __tablename__: str = "card_pools"

    id: int = sqlmodel.Field(primary_key=True, index=True, default=None)
    name: str = sqlmodel.Field(max_length=100, index=True)
