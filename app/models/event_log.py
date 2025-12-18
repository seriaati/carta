import sqlmodel

from app.core.enums import EventType

from ._base import BaseModel


class EventLog(BaseModel, table=True):
    __tablename__: str = "event_logs"

    id: int = sqlmodel.Field(primary_key=True, index=True, default=None)
    player_id: int = sqlmodel.Field(
        foreign_key="players.id", index=True, sa_type=sqlmodel.BigInteger
    )
    event_type: EventType
    context: dict = sqlmodel.Field(sa_column=sqlmodel.Column(sqlmodel.JSON))
