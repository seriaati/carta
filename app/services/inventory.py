from collections.abc import Sequence
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy import func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_db
from app.core.enums import CardRarity, EventType
from app.models.card import Card
from app.models.event_log import EventLog
from app.models.inventory import Inventory
from app.models.player import Player
from app.schemas.common import PaginationData
from app.schemas.inventory import InventoryUpdate, SellCardResponse
from app.services.deck_card import DeckCardService


class InventoryService:
    def __init__(
        self,
        db: Annotated[AsyncSession, Depends(get_db)],
        deck_card_service: Annotated[DeckCardService, Depends()],
    ) -> None:
        self.db = db
        self.deck_card_service = deck_card_service

    async def get_inventories(
        self, *, page: int, page_size: int
    ) -> tuple[Sequence[Inventory], PaginationData]:
        offset = (page - 1) * page_size

        total_items_result = await self.db.exec(select(Inventory))
        total_items = len(total_items_result.all())

        total_pages = (total_items + page_size - 1) // page_size

        result = await self.db.exec(select(Inventory).offset(offset).limit(page_size))
        inventories = result.all()

        pagination = PaginationData(
            page=page, page_size=page_size, total_items=total_items, total_pages=total_pages
        )

        return inventories, pagination

    async def get_inventory(self, inventory_id: int) -> Inventory | None:
        result = await self.db.exec(select(Inventory).where(Inventory.id == inventory_id))
        return result.first()

    async def create_inventory(self, inventory: Inventory) -> Inventory:
        self.db.add(inventory)
        await self.db.commit()
        await self.db.refresh(inventory)
        return inventory

    async def update_inventory(
        self, inventory_id: int, inventory: InventoryUpdate
    ) -> Inventory | None:
        existing_inventory = await self.get_inventory(inventory_id)
        if not existing_inventory:
            return None

        inventory_data = inventory.model_dump(exclude_unset=True)
        existing_inventory.sqlmodel_update(inventory_data)
        self.db.add(existing_inventory)
        await self.db.commit()
        await self.db.refresh(existing_inventory)
        return existing_inventory

    async def delete_inventory(self, inventory_id: int) -> bool:
        inventory = await self.get_inventory(inventory_id)
        if not inventory:
            return False

        await self.db.delete(inventory)
        await self.db.commit()
        return True

    async def get_player_cards(
        self, player_id: int, *, rarity: CardRarity | None = None, card_id: int | None = None
    ) -> Sequence[tuple[Card, int, int]]:
        """Get all cards owned by a player with their quantities and owner counts.

        Returns:
            A sequence of tuples containing (Card, quantity, owner_count).
            owner_count is the number of distinct players who own this card.
        """
        # Subquery to count distinct players who own each card
        owner_count_subquery = (
            select(
                Inventory.card_id,
                func.count(func.distinct(Inventory.player_id)).label("owner_count"),
            )
            .where(Inventory.card_id != None)  # noqa: E711
            .group_by(col(Inventory.card_id))
            .subquery()
        )

        stmt = (
            select(Card, Inventory.quantity, owner_count_subquery.c.owner_count)
            .join(Inventory, col(Card.id) == Inventory.card_id)
            .join(owner_count_subquery, col(Card.id) == owner_count_subquery.c.card_id)
            .where(Inventory.player_id == player_id)
            .where(Inventory.card_id != None)  # noqa: E711
        )

        if rarity is not None:
            stmt = stmt.where(Card.rarity == rarity)

        if card_id is not None:
            stmt = stmt.where(Card.id == card_id)

        result = await self.db.exec(stmt)
        return result.all()

    async def sell_card(self, player_id: int, card_id: int, quantity: int = 1) -> SellCardResponse:
        """Sell a specific quantity of a card for currency.

        Args:
            player_id: The player's ID
            card_id: The card's ID
            quantity: Number of cards to sell (default: 1)

        Returns:
            SellCardResponse containing sold card info, quantity, total_value, and new balance

        Raises:
            HTTPException: If player not found, card not found, or insufficient cards
        """
        # Validate quantity
        if quantity < 1:
            raise HTTPException(status_code=400, detail="數量必須至少為 1")

        # Get player
        player_result = await self.db.exec(select(Player).where(Player.id == player_id))
        player = player_result.first()
        if not player:
            raise HTTPException(status_code=404, detail="找不到玩家")

        # Get card
        card_result = await self.db.exec(select(Card).where(Card.id == card_id))
        card = card_result.first()
        if not card:
            raise HTTPException(status_code=404, detail="找不到卡片")

        # Get inventory
        inventory_result = await self.db.exec(
            select(Inventory).where(Inventory.player_id == player_id, Inventory.card_id == card_id)
        )
        inventory = inventory_result.first()

        if not inventory or inventory.quantity < quantity:
            owned = inventory.quantity if inventory else 0
            raise HTTPException(
                status_code=400, detail=f"卡片數量不足。擁有: {owned}, 需要: {quantity}"
            )

        # Calculate total value
        total_value = card.price * quantity

        # Update inventory
        inventory.quantity -= quantity
        if inventory.quantity == 0:
            await self.db.delete(inventory)
        else:
            self.db.add(inventory)

        # Update player currency
        player.currency += total_value
        self.db.add(player)

        # Log event
        event_log = EventLog(
            player_id=player_id,
            event_type=EventType.SELL_CARD,
            context={
                "card_id": card_id,
                "card_name": card.name,
                "quantity": quantity,
                "unit_price": card.price,
                "total_value": total_value,
            },
        )
        self.db.add(event_log)

        card_name = card.name
        card_price = card.price

        await self.db.commit()

        # Remove sold cards from deck (if any)
        await self.deck_card_service.remove_card_instances_from_deck(
            player_id=player_id, card_id=card_id, quantity=quantity
        )

        await self.db.refresh(player)

        return SellCardResponse(
            card_id=card_id,
            card_name=card_name,
            quantity_sold=quantity,
            unit_price=card_price,
            total_value=total_value,
            new_currency_balance=player.currency,
        )

    async def sell_all_cards(self, player_id: int, card_id: int) -> SellCardResponse:
        """Sell all copies of a specific card for currency.

        Args:
            player_id: The player's ID
            card_id: The card's ID

        Returns:
            SellCardResponse containing sold card info, quantity, total_value, and new balance

        Raises:
            HTTPException: If player not found, card not found, or player doesn't own the card
        """
        # Get player
        player_result = await self.db.exec(select(Player).where(Player.id == player_id))
        player = player_result.first()
        if not player:
            raise HTTPException(status_code=404, detail="找不到玩家")

        # Get card
        card_result = await self.db.exec(select(Card).where(Card.id == card_id))
        card = card_result.first()
        if not card:
            raise HTTPException(status_code=404, detail="找不到卡片")

        # Get inventory
        inventory_result = await self.db.exec(
            select(Inventory).where(Inventory.player_id == player_id, Inventory.card_id == card_id)
        )
        inventory = inventory_result.first()

        if not inventory or inventory.quantity == 0:
            raise HTTPException(status_code=400, detail="你沒有擁有這張卡片")

        # Get quantity to sell
        quantity = inventory.quantity

        # Calculate total value
        total_value = card.price * quantity

        # Delete inventory record
        await self.db.delete(inventory)

        # Update player currency
        player.currency += total_value
        self.db.add(player)

        # Log event
        event_log = EventLog(
            player_id=player_id,
            event_type=EventType.SELL_CARD,
            context={
                "card_id": card_id,
                "card_name": card.name,
                "quantity": quantity,
                "unit_price": card.price,
                "total_value": total_value,
                "sold_all": True,
            },
        )
        self.db.add(event_log)

        await self.db.commit()

        # Remove all instances of this card from deck
        await self.deck_card_service.remove_card_instances_from_deck(
            player_id=player_id, card_id=card_id, quantity=None
        )

        await self.db.refresh(player)

        return SellCardResponse(
            card_id=card_id,
            card_name=card.name,
            quantity_sold=quantity,
            unit_price=card.price,
            total_value=total_value,
            new_currency_balance=player.currency,
        )
