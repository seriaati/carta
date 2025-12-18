from collections.abc import Sequence
from typing import Annotated

from fastapi import Depends
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_db
from app.models.card import Card
from app.models.card_pool import CardPool
from app.models.card_pool_card import CardPoolCard
from app.schemas.card_pool import CardPoolUpdate
from app.schemas.common import PaginationData


class CardPoolService:
    def __init__(self, db: Annotated[AsyncSession, Depends(get_db)]) -> None:
        self.db = db

    async def get_card_pools(
        self, *, page: int, page_size: int
    ) -> tuple[Sequence[CardPool], PaginationData]:
        offset = (page - 1) * page_size

        total_items_result = await self.db.exec(select(CardPool))
        total_items = len(total_items_result.all())

        total_pages = (total_items + page_size - 1) // page_size

        result = await self.db.exec(select(CardPool).offset(offset).limit(page_size))
        card_pools = result.all()

        pagination = PaginationData(
            page=page, page_size=page_size, total_items=total_items, total_pages=total_pages
        )

        return card_pools, pagination

    async def get_all_card_pools(self) -> Sequence[CardPool]:
        result = await self.db.exec(select(CardPool))
        return result.all()

    async def get_card_pool(self, card_pool_id: int) -> CardPool | None:
        result = await self.db.exec(select(CardPool).where(CardPool.id == card_pool_id))
        return result.first()

    async def create_card_pool(self, card_pool: CardPool) -> CardPool:
        self.db.add(card_pool)
        await self.db.commit()
        await self.db.refresh(card_pool)
        return card_pool

    async def update_card_pool(
        self, card_pool_id: int, card_pool: CardPoolUpdate
    ) -> CardPool | None:
        existing_card_pool = await self.get_card_pool(card_pool_id)
        if not existing_card_pool:
            return None

        card_pool_data = card_pool.model_dump(exclude_unset=True)
        existing_card_pool.sqlmodel_update(card_pool_data)
        self.db.add(existing_card_pool)
        await self.db.commit()
        await self.db.refresh(existing_card_pool)
        return existing_card_pool

    async def delete_card_pool(self, card_pool_id: int) -> bool:
        card_pool = await self.get_card_pool(card_pool_id)
        if not card_pool:
            return False

        await self.db.delete(card_pool)
        await self.db.commit()
        return True

    async def get_card_pool_cards(self, card_pool_id: int) -> Sequence[tuple[int, Card, float]]:
        """Get all cards in a card pool with their probabilities.

        Returns:
            List of tuples containing (card_pool_card_id, Card, probability)
        """
        result = await self.db.exec(
            select(CardPoolCard.id, Card, CardPoolCard.probability)
            .join(CardPoolCard, col(CardPoolCard.card_id) == Card.id)
            .where(CardPoolCard.pool_id == card_pool_id)
        )
        return result.all()

    async def get_card_pool_cards_by_rarity(
        self, card_pool_id: int, rarity: str
    ) -> Sequence[tuple[int, Card, float]]:
        """Get all cards in a card pool filtered by rarity with their probabilities.

        Args:
            card_pool_id: The ID of the card pool
            rarity: The rarity to filter by (e.g., 'C', 'R', 'SR', 'SSR', 'UR', 'LR', 'EX')

        Returns:
            List of tuples containing (card_pool_card_id, Card, probability)
        """
        result = await self.db.exec(
            select(CardPoolCard.id, Card, CardPoolCard.probability)
            .join(CardPoolCard, col(CardPoolCard.card_id) == Card.id)
            .where(CardPoolCard.pool_id == card_pool_id, Card.rarity == rarity)
        )
        return result.all()
