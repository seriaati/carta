from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.enums import EventType
from app.core.security import require_admin
from app.models.event_log import EventLog
from app.models.player import Player
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.event_log import EventLogUpdate, EventLogWithPlayer
from app.services.event_log import EventLogService

router = APIRouter(prefix="/event-logs", tags=["event-logs"])


@router.get("/")
async def get_event_logs(  # noqa: PLR0913, PLR0917
    service: Annotated[EventLogService, Depends()],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1)] = 10,
    player_id: Annotated[int | None, Query(description="Filter by player ID")] = None,
    player_name: Annotated[
        str | None, Query(description="Filter by player name (case-insensitive partial match)")
    ] = None,
    event_type: Annotated[EventType | None, Query(description="Filter by event type")] = None,
) -> PaginatedResponse[Sequence[EventLogWithPlayer]]:
    event_logs, pagination = await service.get_event_logs(
        page=page,
        page_size=page_size,
        player_id=player_id,
        player_name=player_name,
        event_type=event_type,
    )
    return PaginatedResponse(data=event_logs, pagination=pagination)


@router.get("/{event_log_id}")
async def get_event_log(
    event_log_id: int, service: Annotated[EventLogService, Depends()]
) -> APIResponse[EventLogWithPlayer]:
    event_log = await service.get_event_log(event_log_id)
    if not event_log:
        raise HTTPException(status_code=404, detail="找不到事件記錄")
    return APIResponse(data=event_log)


@router.post("/")
async def create_event_log(
    event_log: EventLog,
    service: Annotated[EventLogService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[EventLog]:
    created_event_log = await service.create_event_log(event_log)
    return APIResponse(data=created_event_log, message="Event log created successfully")


@router.put("/{event_log_id}")
async def update_event_log(
    event_log_id: int,
    event_log: EventLogUpdate,
    service: Annotated[EventLogService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[EventLog]:
    updated_event_log = await service.update_event_log(event_log_id, event_log)
    if not updated_event_log:
        raise HTTPException(status_code=404, detail="找不到事件記錄")
    return APIResponse(data=updated_event_log, message="Event log updated successfully")


@router.delete("/{event_log_id}")
async def delete_event_log(
    event_log_id: int,
    service: Annotated[EventLogService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[None]:
    deleted = await service.delete_event_log(event_log_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="找不到事件記錄")
    return APIResponse(message="Event log deleted successfully")
