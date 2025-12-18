import sqlmodel

from ._base import BaseModel


class GachaPity(BaseModel, table=True):
    """Track player's pity count for each card pool."""

    __tablename__: str = "gacha_pity"

    id: int = sqlmodel.Field(primary_key=True, index=True, default=None)
    player_id: int = sqlmodel.Field(
        foreign_key="players.id", index=True, sa_type=sqlmodel.BigInteger
    )
    pool_id: int = sqlmodel.Field(foreign_key="card_pools.id", index=True)
    pity_count: int = sqlmodel.Field(default=0, ge=0)
    """Number of pulls since last SSR or higher rarity card"""
