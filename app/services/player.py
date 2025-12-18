from collections.abc import Sequence
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_db
from app.core.enums import CardRarity, EventType
from app.models.card import Card
from app.models.event_log import EventLog
from app.models.inventory import Inventory
from app.models.player import Player
from app.schemas.common import PaginationData
from app.schemas.player import CardStatistics, PlayerUpdate


class PlayerService:
    def __init__(self, db: Annotated[AsyncSession, Depends(get_db)]) -> None:
        self.db = db

    async def get_players(
        self, *, page: int, page_size: int
    ) -> tuple[Sequence[Player], PaginationData]:
        offset = (page - 1) * page_size

        total_items_result = await self.db.exec(select(Player))
        total_items = len(total_items_result.all())

        total_pages = (total_items + page_size - 1) // page_size

        result = await self.db.exec(select(Player).offset(offset).limit(page_size))
        players = result.all()

        pagination = PaginationData(
            page=page, page_size=page_size, total_items=total_items, total_pages=total_pages
        )

        return players, pagination

    async def get_player(self, player_id: int) -> Player | None:
        result = await self.db.exec(select(Player).where(Player.id == player_id))
        return result.first()

    async def create_player(self, player: Player) -> Player:
        self.db.add(player)
        await self.db.commit()
        await self.db.refresh(player)
        return player

    async def update_player(self, player_id: int, player: PlayerUpdate) -> Player | None:
        existing_player = await self.get_player(player_id)
        if not existing_player:
            return None

        player_data = player.model_dump(exclude_unset=True)
        existing_player.sqlmodel_update(player_data)
        self.db.add(existing_player)
        await self.db.commit()
        await self.db.refresh(existing_player)
        return existing_player

    async def delete_player(self, player_id: int) -> bool:
        player = await self.get_player(player_id)
        if not player:
            return False

        await self.db.delete(player)
        await self.db.commit()
        return True

    async def _log_currency_event(
        self, player_id: int, event_type: EventType, amount: int, reason: str
    ) -> None:
        """Log a currency event to the event log."""
        event_log = EventLog(
            player_id=player_id, event_type=event_type, context={"amount": amount, "reason": reason}
        )
        self.db.add(event_log)

    async def increase_currency(self, player_id: int, amount: int, reason: str) -> Player:
        """Increase a player's currency and log the event."""
        player = await self.get_player(player_id)
        if not player:
            raise HTTPException(status_code=404, detail="找不到玩家")

        player.currency += amount
        self.db.add(player)

        await self._log_currency_event(player_id, EventType.ADMIN_INCREASE_CURRENCY, amount, reason)

        await self.db.commit()
        await self.db.refresh(player)
        return player

    async def decrease_currency(self, player_id: int, amount: int, reason: str) -> Player:
        """Decrease a player's currency and log the event.

        Raises:
            HTTPException: If player not found or insufficient funds.
        """
        player = await self.get_player(player_id)
        if not player:
            raise HTTPException(status_code=404, detail="找不到玩家")

        if player.currency < amount:
            raise HTTPException(
                status_code=400, detail=f"貨幣不足。目前: {player.currency}, 需要: {amount}"
            )

        player.currency -= amount
        self.db.add(player)

        await self._log_currency_event(player_id, EventType.ADMIN_DECREASE_CURRENCY, amount, reason)

        await self.db.commit()
        await self.db.refresh(player)
        return player

    async def set_currency(self, player_id: int, amount: int, reason: str) -> Player:
        """Set a player's currency to a specific amount and log the event."""
        player = await self.get_player(player_id)
        if not player:
            raise HTTPException(status_code=404, detail="找不到玩家")

        old_amount = player.currency
        player.currency = amount
        self.db.add(player)

        await self._log_currency_event(
            player_id,
            EventType.ADMIN_SET_CURRENCY,
            amount,
            f"Set from {old_amount} to {amount}: {reason}",
        )

        await self.db.commit()
        await self.db.refresh(player)
        return player

    async def get_card_statistics(self, player_id: int) -> CardStatistics:
        """Get card statistics for a player.

        Returns:
            CardStatistics object with total owned cards and counts per rarity.
        """
        # Get total owned cards
        total_result = await self.db.exec(
            select(func.sum(Inventory.quantity))
            .where(Inventory.player_id == player_id)
            .where(Inventory.card_id != None)  # noqa: E711
        )
        total_owned = total_result.one() or 0

        # Get cards per rarity
        rarity_result = await self.db.exec(
            select(Card.rarity, func.sum(Inventory.quantity))
            .join(Inventory, col(Inventory.card_id) == Card.id)
            .where(Inventory.player_id == player_id)
            .group_by(Card.rarity)
        )

        cards_per_rarity: dict[CardRarity, int] = dict.fromkeys(CardRarity, 0)
        for rarity, count in rarity_result.all():
            cards_per_rarity[CardRarity(rarity)] = count or 0

        return CardStatistics(total_owned_cards=total_owned, cards_per_rarity=cards_per_rarity)
