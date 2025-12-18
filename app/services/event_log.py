from collections.abc import Sequence
from typing import Annotated

from fastapi import Depends
from sqlmodel import col, desc, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_db
from app.core.enums import EventType
from app.models.event_log import EventLog
from app.models.player import Player
from app.schemas.common import PaginationData
from app.schemas.event_log import EventLogUpdate, EventLogWithPlayer


class EventLogService:
    def __init__(self, db: Annotated[AsyncSession, Depends(get_db)]) -> None:
        self.db = db

    async def get_event_logs(
        self,
        *,
        page: int,
        page_size: int,
        player_id: int | None = None,
        player_name: str | None = None,
        event_type: EventType | None = None,
    ) -> tuple[Sequence[EventLogWithPlayer], PaginationData]:
        offset = (page - 1) * page_size

        # Build base query with filters
        count_query = select(EventLog).join(Player, col(EventLog.player_id) == col(Player.id))
        main_query = select(EventLog, Player.name).join(
            Player, col(EventLog.player_id) == col(Player.id)
        )

        # Apply filters
        filters = []
        if player_id is not None:
            filters.append(col(EventLog.player_id) == player_id)
        if player_name is not None:
            # Case-insensitive partial match
            filters.append(col(Player.name).ilike(f"%{player_name}%"))
        if event_type is not None:
            filters.append(col(EventLog.event_type) == event_type)

        if filters:
            count_query = count_query.where(*filters)
            main_query = main_query.where(*filters)

        # Get total count
        total_items_result = await self.db.exec(count_query)
        total_items = len(total_items_result.all())

        total_pages = (total_items + page_size - 1) // page_size

        # Get paginated results
        result = await self.db.exec(
            main_query.order_by(desc(col(EventLog.created_at))).offset(offset).limit(page_size)
        )
        rows = result.all()

        event_logs_with_player = [
            EventLogWithPlayer(
                id=event_log.id,
                player_id=event_log.player_id,
                player_name=player_name,
                event_type=event_log.event_type,
                context=event_log.context,
                created_at=event_log.created_at,
                updated_at=event_log.updated_at,
            )
            for event_log, player_name in rows
        ]

        pagination = PaginationData(
            page=page, page_size=page_size, total_items=total_items, total_pages=total_pages
        )

        return event_logs_with_player, pagination

    async def get_event_log(self, event_log_id: int) -> EventLogWithPlayer | None:
        result = await self.db.exec(
            select(EventLog, Player.name)
            .join(Player, col(EventLog.player_id) == col(Player.id))
            .where(EventLog.id == event_log_id)
        )
        row = result.first()
        if not row:
            return None

        event_log, player_name = row
        return EventLogWithPlayer(
            id=event_log.id,
            player_id=event_log.player_id,
            player_name=player_name,
            event_type=event_log.event_type,
            context=event_log.context,
            created_at=event_log.created_at,
            updated_at=event_log.updated_at,
        )

    async def _get_event_log_raw(self, event_log_id: int) -> EventLog | None:
        """Get raw EventLog without player join (for internal use)."""
        result = await self.db.exec(select(EventLog).where(EventLog.id == event_log_id))
        return result.first()

    async def create_event_log(self, event_log: EventLog) -> EventLog:
        self.db.add(event_log)
        await self.db.commit()
        await self.db.refresh(event_log)
        return event_log

    async def update_event_log(
        self, event_log_id: int, event_log: EventLogUpdate
    ) -> EventLog | None:
        existing_event_log = await self._get_event_log_raw(event_log_id)
        if not existing_event_log:
            return None

        event_log_data = event_log.model_dump(exclude_unset=True)
        existing_event_log.sqlmodel_update(event_log_data)
        self.db.add(existing_event_log)
        await self.db.commit()
        await self.db.refresh(existing_event_log)
        return existing_event_log

    async def delete_event_log(self, event_log_id: int) -> bool:
        event_log = await self._get_event_log_raw(event_log_id)
        if not event_log:
            return False

        await self.db.delete(event_log)
        await self.db.commit()
        return True
