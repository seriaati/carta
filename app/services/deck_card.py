from collections.abc import Sequence
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_db
from app.models.card import Card
from app.models.deck_card import DeckCard
from app.models.inventory import Inventory
from app.schemas.common import PaginationData
from app.schemas.deck_card import DeckCardUpdate


class DeckCardService:
    def __init__(self, db: Annotated[AsyncSession, Depends(get_db)]) -> None:
        self.db = db

    async def get_deck_cards(
        self, *, page: int, page_size: int
    ) -> tuple[Sequence[DeckCard], PaginationData]:
        offset = (page - 1) * page_size

        total_items_result = await self.db.exec(select(DeckCard))
        total_items = len(total_items_result.all())

        total_pages = (total_items + page_size - 1) // page_size

        result = await self.db.exec(select(DeckCard).offset(offset).limit(page_size))
        deck_cards = result.all()

        pagination = PaginationData(
            page=page, page_size=page_size, total_items=total_items, total_pages=total_pages
        )

        return deck_cards, pagination

    async def get_deck_card(self, deck_card_id: int) -> DeckCard | None:
        result = await self.db.exec(select(DeckCard).where(DeckCard.id == deck_card_id))
        return result.first()

    async def create_deck_card(self, deck_card: DeckCard) -> DeckCard:
        self.db.add(deck_card)
        await self.db.commit()
        await self.db.refresh(deck_card)
        return deck_card

    async def update_deck_card(
        self, deck_card_id: int, deck_card: DeckCardUpdate
    ) -> DeckCard | None:
        existing_deck_card = await self.get_deck_card(deck_card_id)
        if not existing_deck_card:
            return None

        deck_card_data = deck_card.model_dump(exclude_unset=True)
        existing_deck_card.sqlmodel_update(deck_card_data)
        self.db.add(existing_deck_card)
        await self.db.commit()
        await self.db.refresh(existing_deck_card)
        return existing_deck_card

    async def delete_deck_card(self, deck_card_id: int) -> bool:
        deck_card = await self.get_deck_card(deck_card_id)
        if not deck_card:
            return False

        await self.db.delete(deck_card)
        await self.db.commit()
        return True

    async def remove_card_from_deck(self, *, player_id: int, position: int) -> bool:
        """Remove a card from the deck at the specified position for a player."""
        result = await self.db.exec(
            select(DeckCard).where(DeckCard.player_id == player_id, DeckCard.position == position)
        )
        deck_card = result.first()

        if not deck_card:
            return False

        await self.db.delete(deck_card)
        await self.db.commit()
        return True

    async def clear_player_deck(self, *, player_id: int) -> int:
        """Remove all cards from a player's deck. Returns the number of cards removed."""
        result = await self.db.exec(select(DeckCard).where(DeckCard.player_id == player_id))
        deck_cards = result.all()

        count = len(deck_cards)
        for deck_card in deck_cards:
            await self.db.delete(deck_card)

        await self.db.commit()
        return count

    async def remove_card_instances_from_deck(
        self, *, player_id: int, card_id: int, quantity: int | None = None
    ) -> int:
        """Remove instances of a specific card from a player's deck.

        Args:
            player_id: The player's ID
            card_id: The card's ID to remove
            quantity: Number of instances to remove. If None, removes all instances.

        Returns:
            The number of deck card instances removed.
        """
        result = await self.db.exec(
            select(DeckCard).where(DeckCard.player_id == player_id, DeckCard.card_id == card_id)
        )
        deck_cards = result.all()

        # Determine how many to remove
        to_remove = len(deck_cards) if quantity is None else min(quantity, len(deck_cards))

        # Remove the specified number of instances
        for i in range(to_remove):
            await self.db.delete(deck_cards[i])

        await self.db.commit()
        return to_remove

    async def count_card_in_deck(self, *, player_id: int, card_id: int) -> int:
        """Count how many times a specific card appears in a player's deck."""
        result = await self.db.exec(
            select(func.count(col(DeckCard.id))).where(
                DeckCard.player_id == player_id, DeckCard.card_id == card_id
            )
        )
        return result.one()

    async def add_card_to_deck(self, *, player_id: int, card_id: int, position: int) -> DeckCard:
        # Check if player owns the card and get the quantity
        inventory_result = await self.db.exec(
            select(Inventory).where(Inventory.player_id == player_id, Inventory.card_id == card_id)
        )
        inventory = inventory_result.first()

        if not inventory or inventory.quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="你沒有擁有這張卡牌。"
            )

        # Check if there's already a card at this position
        existing_position_result = await self.db.exec(
            select(DeckCard).where(DeckCard.player_id == player_id, DeckCard.position == position)
        )
        existing_at_position = existing_position_result.first()

        # Check how many times this card is already in the deck
        card_count_in_deck = await self.count_card_in_deck(player_id=player_id, card_id=card_id)

        # If there's already a card at this position with the same card_id, we're just replacing it
        # So we shouldn't count it against the inventory limit
        if existing_at_position and existing_at_position.card_id == card_id:
            card_count_in_deck -= 1

        if card_count_in_deck >= inventory.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"你只擁有 {inventory.quantity} 張這張卡牌，無法再加入牌組。",
            )

        # Remove existing card at this position if it exists
        if existing_at_position:
            await self.db.delete(existing_at_position)

        deck_card = DeckCard(player_id=player_id, card_id=card_id, position=position)
        self.db.add(deck_card)
        await self.db.commit()
        await self.db.refresh(deck_card)
        return deck_card

    async def get_player_deck(self, player_id: int) -> Sequence[tuple[DeckCard, Card]]:
        """
        Get a player's deck with card details, maximum 6 cards.
        Returns a list of tuples (DeckCard, Card) ordered by position.
        """
        result = await self.db.exec(
            select(DeckCard, Card)
            .join(Card, col(DeckCard.card_id) == Card.id)
            .where(DeckCard.player_id == player_id)
            .order_by(col(DeckCard.position))
            .limit(6)
        )
        return result.all()
