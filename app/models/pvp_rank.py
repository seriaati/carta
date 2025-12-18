from datetime import datetime

import sqlmodel

from ._base import BaseModel


class PvPRank(BaseModel, table=True):
    __tablename__: str = "pvp_ranks"

    id: int = sqlmodel.Field(primary_key=True, index=True, default=None)
    player_id: int = sqlmodel.Field(
        foreign_key="players.id", index=True, sa_type=sqlmodel.BigInteger
    )
    points: int = sqlmodel.Field(default=50, ge=0)
    week: int = sqlmodel.Field(index=True)
    score_updated_at: datetime = sqlmodel.Field(
        default_factory=datetime.now, sa_type=sqlmodel.DateTime(timezone=True)
    )
    daily_plays: int = sqlmodel.Field(default=0, ge=0)
    last_play_date: datetime | None = sqlmodel.Field(
        default=None, nullable=True, sa_type=sqlmodel.DateTime(timezone=True)
    )
    daily_bet_amount: int = sqlmodel.Field(default=0, ge=0)
    last_bet_date: datetime | None = sqlmodel.Field(
        default=None, nullable=True, sa_type=sqlmodel.DateTime(timezone=True)
    )
