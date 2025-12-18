from __future__ import annotations

from datetime import datetime

import sqlmodel

from ._base import BaseModel


class Session(BaseModel, table=True):
    __tablename__: str = "sessions"

    id: int | None = sqlmodel.Field(default=None, primary_key=True)
    player_id: int = sqlmodel.Field(
        index=True, sa_type=sqlmodel.BigInteger, foreign_key="players.id"
    )
    token_hash: str = sqlmodel.Field(index=True)
    revoked: bool = False
    expires_at: datetime = sqlmodel.Field(sa_type=sqlmodel.DateTime(timezone=True))
