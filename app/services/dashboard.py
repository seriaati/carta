from typing import Annotated

from fastapi import Depends
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_db
from app.core.enums import PvPStatus, TradeStatus
from app.models.card import Card
from app.models.card_pool import CardPool
from app.models.deck_card import DeckCard
from app.models.inventory import Inventory
from app.models.player import Player
from app.models.pvp_challenge import PvPChallenge
from app.models.shop_item import ShopItem
from app.models.trade import Trade
from app.schemas.dashboard import DashboardStats


class DashboardService:
    def __init__(self, db: Annotated[AsyncSession, Depends(get_db)]) -> None:
        self.db = db

    async def _count_model(self, model: type) -> int:
        """Count total records for a given model."""
        result = await self.db.exec(select(func.count(model.id)))
        return result.one()

    async def _count_by_status(self, model: type, status_field: str, status_value: str) -> int:
        """Count records filtered by status."""
        result = await self.db.exec(
            select(func.count(model.id)).where(getattr(model, status_field) == status_value)
        )
        return result.one()

    async def get_dashboard_stats(self) -> DashboardStats:
        """Get comprehensive dashboard statistics."""
        return DashboardStats(
            total_players=await self._count_model(Player),
            total_cards=await self._count_model(Card),
            total_card_pools=await self._count_model(CardPool),
            total_trades=await self._count_model(Trade),
            active_trades=await self._count_by_status(Trade, "status", TradeStatus.PENDING),
            total_pvp_challenges=await self._count_model(PvPChallenge),
            active_pvp_challenges=await self._count_by_status(
                PvPChallenge, "status", PvPStatus.PENDING
            ),
            total_shop_items=await self._count_model(ShopItem),
            total_inventory_items=await self._count_model(Inventory),
            total_deck_cards=await self._count_model(DeckCard),
        )
