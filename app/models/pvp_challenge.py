import sqlmodel

from app.core.enums import PvPMode, PvPStatus

from ._base import BaseModel


class PvPChallenge(BaseModel, table=True):
    __tablename__: str = "pvp_challenges"

    id: int = sqlmodel.Field(primary_key=True, index=True, default=None)
    challenger_id: int = sqlmodel.Field(
        foreign_key="players.id", index=True, sa_type=sqlmodel.BigInteger
    )
    opponent_id: int = sqlmodel.Field(
        foreign_key="players.id", index=True, sa_type=sqlmodel.BigInteger
    )
    winner_id: int | None = sqlmodel.Field(
        foreign_key="players.id",
        index=True,
        nullable=True,
        default=None,
        sa_type=sqlmodel.BigInteger,
    )
    bet: int = sqlmodel.Field(default=0, ge=0, le=10_0000)
    status: PvPStatus = PvPStatus.PENDING
    mode: PvPMode = PvPMode.FRIENDLY
