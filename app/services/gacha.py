import random
from collections.abc import Sequence
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_db
from app.core.enums import CardRarity, EventType
from app.models.card import Card
from app.models.card_pool import CardPool
from app.models.card_pool_card import CardPoolCard
from app.models.event_log import EventLog
from app.models.gacha_pity import GachaPity
from app.models.gacha_pull import GachaPull
from app.models.inventory import Inventory
from app.models.player import Player
from app.schemas.gacha import GachaPityResponse, GachaPullResult

MAX_PITY = 1000
SINGLE_PULL_COST = 100
TEN_PULL_COST = 1000


class GachaService:
    def __init__(self, db: Annotated[AsyncSession, Depends(get_db)]) -> None:
        self.db = db

    async def get_or_create_pity(self, player_id: int, pool_id: int) -> GachaPity:
        """Get or create a pity record for a player and pool."""
        result = await self.db.exec(
            select(GachaPity).where(GachaPity.player_id == player_id, GachaPity.pool_id == pool_id)
        )
        pity = result.first()

        if not pity:
            pity = GachaPity(player_id=player_id, pool_id=pool_id, pity_count=0)
            self.db.add(pity)
            await self.db.commit()
            await self.db.refresh(pity)

        return pity

    async def get_pity_count(self, player_id: int, pool_id: int) -> GachaPityResponse:
        """Get the current pity count for a player in a specific pool."""
        # Verify pool exists
        result = await self.db.exec(select(CardPool).where(CardPool.id == pool_id))
        pool = result.first()
        if not pool:
            raise HTTPException(status_code=404, detail="找不到卡池")

        pity = await self.get_or_create_pity(player_id, pool_id)

        return GachaPityResponse(
            pool_id=pool_id, pool_name=pool.name, current_pity=pity.pity_count, max_pity=MAX_PITY
        )

    async def get_pool_cards(self, pool_id: int) -> Sequence[tuple[Card, float]]:
        """Get all cards in a pool with their probabilities."""
        result = await self.db.exec(
            select(Card, CardPoolCard.probability)
            .join(CardPoolCard, col(Card.id) == CardPoolCard.card_id)
            .where(CardPoolCard.pool_id == pool_id)
        )
        return result.all()

    async def get_ssr_cards(self, pool_id: int) -> Sequence[Card]:
        """Get all SSR cards in a pool (for pity guaranteed pulls)."""
        result = await self.db.exec(
            select(Card)
            .join(CardPoolCard, col(Card.id) == CardPoolCard.card_id)
            .where(CardPoolCard.pool_id == pool_id, col(Card.rarity) == CardRarity.SSR)
        )
        return result.all()

    def _select_card_by_probability(
        self, cards: Sequence[tuple[Card, float]], is_pity: bool = False
    ) -> Card:
        """Select a card based on probabilities."""
        if not cards:
            raise HTTPException(status_code=400, detail="此卡池沒有可用的卡片")

        if is_pity:
            # For pity pulls, only consider SSR rarity cards (not higher)
            # Select randomly from those cards (equal probability)
            ssr_cards = [card for card, _ in cards if card.rarity == CardRarity.SSR]
            if not ssr_cards:
                raise HTTPException(status_code=400, detail="此卡池沒有 SSR 稀有度的卡片")
            return random.choice(ssr_cards)

        # Normal pull - use weighted probabilities
        card_list, probabilities = zip(*cards, strict=False)

        # Normalize probabilities to sum to 1
        total_prob = sum(probabilities)
        if total_prob <= 0:
            raise HTTPException(status_code=400, detail="卡池中的機率無效")

        normalized_probs = [p / total_prob for p in probabilities]

        # Select card based on weighted random choice
        return random.choices(list(card_list), weights=normalized_probs, k=1)[0]

    async def perform_single_pull(
        self, player_id: int, pool_id: int, pity: GachaPity, cards: Sequence[tuple[Card, float]]
    ) -> tuple[Card, bool]:
        """Perform a single gacha pull.

        Returns:
            Tuple of (Card, was_pity)
        """
        # Check if pity is triggered
        is_pity = pity.pity_count >= MAX_PITY

        # Select card
        selected_card = self._select_card_by_probability(cards, is_pity=is_pity)

        # Update pity count
        is_ssr_or_higher = selected_card.rarity in {
            CardRarity.SSR,
            CardRarity.UR,
            CardRarity.LR,
            CardRarity.EX,
        }
        if is_ssr_or_higher:
            pity.pity_count = 0
        else:
            pity.pity_count += 1

        # Log the pull
        pull_log = GachaPull(
            player_id=player_id, pool_id=pool_id, card_id=selected_card.id, was_pity=is_pity
        )
        self.db.add(pull_log)

        # Add card to inventory
        inventory_result = await self.db.exec(
            select(Inventory).where(
                Inventory.player_id == player_id, Inventory.card_id == selected_card.id
            )
        )
        inventory = inventory_result.first()

        if inventory:
            inventory.quantity += 1
            self.db.add(inventory)
        else:
            new_inventory = Inventory(player_id=player_id, card_id=selected_card.id, quantity=1)
            self.db.add(new_inventory)

        # Log event
        event_log = EventLog(
            player_id=player_id,
            event_type=EventType.GACHA_PULL,
            context={"card_id": selected_card.id, "pool_id": pool_id, "was_pity": is_pity},
        )
        self.db.add(event_log)

        return selected_card, is_pity

    async def pull_cards(
        self, player_id: int, pool_id: int, count: int
    ) -> tuple[list[GachaPullResult], int]:
        """Perform gacha pulls for a player.

        Args:
            player_id: ID of the player
            pool_id: ID of the card pool
            count: Number of pulls (1 or 10)

        Returns:
            Tuple of (list of pull results, remaining currency)
        """
        # Validate count
        if count not in {1, 10}:
            raise HTTPException(status_code=400, detail="抽卡次數必須為 1 或 10")

        # Calculate cost
        cost = SINGLE_PULL_COST if count == 1 else TEN_PULL_COST

        # Get player
        player_result = await self.db.exec(select(Player).where(Player.id == player_id))
        player = player_result.first()
        if not player:
            raise HTTPException(status_code=404, detail="找不到玩家")

        # Check currency
        if player.currency < cost:
            raise HTTPException(status_code=400, detail="貨幣不足")

        # Verify pool exists
        pool_result = await self.db.exec(select(CardPool).where(CardPool.id == pool_id))
        pool = pool_result.first()
        if not pool:
            raise HTTPException(status_code=404, detail="找不到卡池")

        # Get pool cards
        cards = await self.get_pool_cards(pool_id)
        if not cards:
            raise HTTPException(status_code=400, detail="此卡池沒有卡片")

        # Get or create pity record
        pity = await self.get_or_create_pity(player_id, pool_id)

        # Perform pulls
        results: list[GachaPullResult] = []
        for _ in range(count):
            card, was_pity = await self.perform_single_pull(player_id, pool_id, pity, cards)
            results.append(
                GachaPullResult(
                    card_id=card.id, card_name=card.name, card_rarity=card.rarity, was_pity=was_pity
                )
            )

        # Deduct currency
        player.currency -= cost
        remaining_currency = player.currency
        self.db.add(player)

        # Update pity record
        self.db.add(pity)

        # Commit all changes
        await self.db.commit()

        return results, remaining_currency
