from datetime import datetime

from pydantic import BaseModel

from app.core.enums import EventType


class EventLogUpdate(BaseModel):
    player_id: int | None = None
    event_type: EventType | None = None
    context: dict | None = None


class EventLogWithPlayer(BaseModel):
    id: int
    player_id: int
    player_name: str | None
    event_type: EventType
    context: dict
    created_at: datetime
    updated_at: datetime
