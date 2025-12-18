from collections.abc import Sequence
from typing import Annotated

from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_db
from app.models.pvp_challenge import PvPChallenge
from app.schemas.common import PaginationData
from app.schemas.pvp_challenge import PvPChallengeUpdate


class PvPChallengeService:
    def __init__(self, db: Annotated[AsyncSession, Depends(get_db)]) -> None:
        self.db = db

    async def get_pvp_challenges(
        self, *, page: int, page_size: int
    ) -> tuple[Sequence[PvPChallenge], PaginationData]:
        offset = (page - 1) * page_size

        total_items_result = await self.db.exec(select(PvPChallenge))
        total_items = len(total_items_result.all())

        total_pages = (total_items + page_size - 1) // page_size

        result = await self.db.exec(select(PvPChallenge).offset(offset).limit(page_size))
        pvp_challenges = result.all()

        pagination = PaginationData(
            page=page, page_size=page_size, total_items=total_items, total_pages=total_pages
        )

        return pvp_challenges, pagination

    async def get_pvp_challenge(self, pvp_challenge_id: int) -> PvPChallenge | None:
        result = await self.db.exec(select(PvPChallenge).where(PvPChallenge.id == pvp_challenge_id))
        return result.first()

    async def create_pvp_challenge(self, pvp_challenge: PvPChallenge) -> PvPChallenge:
        self.db.add(pvp_challenge)
        await self.db.commit()
        await self.db.refresh(pvp_challenge)
        return pvp_challenge

    async def update_pvp_challenge(
        self, pvp_challenge_id: int, pvp_challenge: PvPChallengeUpdate
    ) -> PvPChallenge | None:
        existing_pvp_challenge = await self.get_pvp_challenge(pvp_challenge_id)
        if not existing_pvp_challenge:
            return None

        pvp_challenge_data = pvp_challenge.model_dump(exclude_unset=True)
        existing_pvp_challenge.sqlmodel_update(pvp_challenge_data)
        self.db.add(existing_pvp_challenge)
        await self.db.commit()
        await self.db.refresh(existing_pvp_challenge)
        return existing_pvp_challenge

    async def delete_pvp_challenge(self, pvp_challenge_id: int) -> bool:
        pvp_challenge = await self.get_pvp_challenge(pvp_challenge_id)
        if not pvp_challenge:
            return False

        await self.db.delete(pvp_challenge)
        await self.db.commit()
        return True
