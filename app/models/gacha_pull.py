import sqlmodel

from ._base import BaseModel


class GachaPull(BaseModel, table=True):
    """Log each individual gacha pull made by a player."""

    __tablename__: str = "gacha_pulls"

    id: int = sqlmodel.Field(primary_key=True, index=True, default=None)
    player_id: int = sqlmodel.Field(
        foreign_key="players.id", index=True, sa_type=sqlmodel.BigInteger
    )
    pool_id: int = sqlmodel.Field(foreign_key="card_pools.id", index=True)
    card_id: int = sqlmodel.Field(foreign_key="cards.id", index=True)
    was_pity: bool = sqlmodel.Field(default=False)
    """Whether this pull was triggered by the pity system"""
