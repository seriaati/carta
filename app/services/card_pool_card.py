from collections.abc import Sequence
from typing import Annotated

from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_db
from app.models.card_pool_card import CardPoolCard
from app.schemas.card_pool_card import CardPoolCardUpdate
from app.schemas.common import PaginationData


class CardPoolCardService:
    def __init__(self, db: Annotated[AsyncSession, Depends(get_db)]) -> None:
        self.db = db

    async def get_card_pool_cards(
        self, *, page: int, page_size: int
    ) -> tuple[Sequence[CardPoolCard], PaginationData]:
        offset = (page - 1) * page_size

        total_items_result = await self.db.exec(select(CardPoolCard))
        total_items = len(total_items_result.all())

        total_pages = (total_items + page_size - 1) // page_size

        result = await self.db.exec(select(CardPoolCard).offset(offset).limit(page_size))
        card_pool_cards = result.all()

        pagination = PaginationData(
            page=page, page_size=page_size, total_items=total_items, total_pages=total_pages
        )

        return card_pool_cards, pagination

    async def get_card_pool_card(self, card_pool_card_id: int) -> CardPoolCard | None:
        result = await self.db.exec(
            select(CardPoolCard).where(CardPoolCard.id == card_pool_card_id)
        )
        return result.first()

    async def create_card_pool_card(self, card_pool_card: CardPoolCard) -> CardPoolCard:
        self.db.add(card_pool_card)
        await self.db.commit()
        await self.db.refresh(card_pool_card)
        return card_pool_card

    async def update_card_pool_card(
        self, card_pool_card_id: int, card_pool_card: CardPoolCardUpdate
    ) -> CardPoolCard | None:
        existing_card_pool_card = await self.get_card_pool_card(card_pool_card_id)
        if not existing_card_pool_card:
            return None

        card_pool_card_data = card_pool_card.model_dump(exclude_unset=True)
        existing_card_pool_card.sqlmodel_update(card_pool_card_data)
        self.db.add(existing_card_pool_card)
        await self.db.commit()
        await self.db.refresh(existing_card_pool_card)
        return existing_card_pool_card

    async def delete_card_pool_card(self, card_pool_card_id: int) -> bool:
        card_pool_card = await self.get_card_pool_card(card_pool_card_id)
        if not card_pool_card:
            return False

        await self.db.delete(card_pool_card)
        await self.db.commit()
        return True
