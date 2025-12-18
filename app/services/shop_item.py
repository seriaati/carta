import random
from collections.abc import Sequence
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_db
from app.core.enums import EventType, ShopItemType
from app.models.card import Card
from app.models.event_log import EventLog
from app.models.inventory import Inventory
from app.models.player import Player
from app.models.shop_item import ShopItem
from app.schemas.common import PaginationData
from app.schemas.shop_item import ShopItemResponse, ShopItemUpdate
from app.utils.misc import get_utc_now


class ShopItemService:
    def __init__(self, db: Annotated[AsyncSession, Depends(get_db)]) -> None:
        self.db = db

    async def get_shop_items(
        self, *, page: int, page_size: int
    ) -> tuple[Sequence[ShopItemResponse], PaginationData]:
        offset = (page - 1) * page_size

        total_items_result = await self.db.exec(select(ShopItem))
        total_items = len(total_items_result.all())

        total_pages = (total_items + page_size - 1) // page_size

        result = await self.db.exec(select(ShopItem).offset(offset).limit(page_size))
        shop_items = result.all()

        # Fetch cards for shop items that have card_id
        shop_items_response = []
        for shop_item in shop_items:
            card = None
            if shop_item.card_id:
                card_result = await self.db.exec(select(Card).where(Card.id == shop_item.card_id))
                card = card_result.first()

            shop_items_response.append(
                ShopItemResponse(
                    id=shop_item.id,
                    name=shop_item.name,
                    price=shop_item.price,
                    type=shop_item.type,
                    rate=shop_item.rate,
                    card_id=shop_item.card_id,
                    card=card,
                    created_at=shop_item.created_at.isoformat(),
                    updated_at=shop_item.updated_at.isoformat(),
                )
            )

        pagination = PaginationData(
            page=page, page_size=page_size, total_items=total_items, total_pages=total_pages
        )

        return shop_items_response, pagination

    async def get_all_shop_items(self) -> Sequence[ShopItem]:
        result = await self.db.exec(select(ShopItem).options(selectinload(ShopItem.card)))
        return result.all()

    def _convert_to_response(self, shop_item: ShopItem) -> ShopItemResponse:
        """Convert a ShopItem to ShopItemResponse."""
        return ShopItemResponse(
            id=shop_item.id,
            name=shop_item.name,
            price=shop_item.price,
            type=shop_item.type,
            rate=shop_item.rate,
            card_id=shop_item.card_id,
            card=shop_item.card or None,
            created_at=shop_item.created_at.isoformat(),
            updated_at=shop_item.updated_at.isoformat(),
        )

    async def get_dynamic_shop_items(self, player_id: int) -> list[ShopItem]:  # noqa: PLR0914
        """Get dynamic shop items for a player.

        Returns 10 random items (same for all players weekly) + 3 random items (player-specific daily).
        Uses the 'rate' field to determine probability of items appearing.
        Duplicates are removed while preserving order.

        Args:
            player_id: The ID of the player viewing the shop.

        Returns:
            A list of unique shop items (up to 10 global + 3 player-specific).
        """
        # Get all shop items with preloaded card data
        all_items = await self.get_all_shop_items()
        if not all_items:
            return []

        items_list = list(all_items)
        rates = [item.rate for item in items_list]

        # Calculate seeds for random selection
        current_date = get_utc_now().date()
        iso_year, iso_week, _ = current_date.isocalendar()
        weekly_seed = iso_year * 100 + iso_week
        daily_seed = int(current_date.strftime("%Y%m%d"))

        # Generate 10 global items (same for all players this week)
        # Use instance-based random generator to avoid global state issues
        global_rng = random.Random(weekly_seed)
        global_items = global_rng.choices(items_list, weights=rates, k=min(10, len(items_list)))

        # Generate 3 player-specific items (unique per player, changes daily)
        player_rng = random.Random(daily_seed + player_id)
        player_items = player_rng.choices(items_list, weights=rates, k=min(3, len(items_list)))

        # Combine and remove duplicates while preserving order
        combined_items = global_items + player_items
        seen_ids = set()
        unique_items = []
        for item in combined_items:
            if item.id not in seen_ids:
                seen_ids.add(item.id)
                unique_items.append(item)

        return unique_items

    async def get_shop_item(self, shop_item_id: int) -> ShopItemResponse | None:
        result = await self.db.exec(select(ShopItem).where(ShopItem.id == shop_item_id))
        shop_item = result.first()
        if not shop_item:
            return None

        card = None
        if shop_item.card_id:
            card_result = await self.db.exec(select(Card).where(Card.id == shop_item.card_id))
            card = card_result.first()

        return ShopItemResponse(
            id=shop_item.id,
            name=shop_item.name,
            price=shop_item.price,
            type=shop_item.type,
            rate=shop_item.rate,
            card_id=shop_item.card_id,
            card=card,
            created_at=shop_item.created_at.isoformat(),
            updated_at=shop_item.updated_at.isoformat(),
        )

    async def create_shop_item(self, shop_item: ShopItem) -> ShopItemResponse:
        self.db.add(shop_item)
        await self.db.commit()
        await self.db.refresh(shop_item)

        card = None
        if shop_item.card_id:
            card_result = await self.db.exec(select(Card).where(Card.id == shop_item.card_id))
            card = card_result.first()

        return ShopItemResponse(
            id=shop_item.id,
            name=shop_item.name,
            price=shop_item.price,
            type=shop_item.type,
            rate=shop_item.rate,
            card_id=shop_item.card_id,
            card=card,
            created_at=shop_item.created_at.isoformat(),
            updated_at=shop_item.updated_at.isoformat(),
        )

    async def update_shop_item(
        self, shop_item_id: int, shop_item: ShopItemUpdate
    ) -> ShopItemResponse | None:
        # Fetch the raw shop item from database
        result = await self.db.exec(select(ShopItem).where(ShopItem.id == shop_item_id))
        existing_shop_item = result.first()
        if not existing_shop_item:
            return None

        shop_item_data = shop_item.model_dump(exclude_unset=True)
        existing_shop_item.sqlmodel_update(shop_item_data)
        self.db.add(existing_shop_item)
        await self.db.commit()
        await self.db.refresh(existing_shop_item)

        card = None
        if existing_shop_item.card_id:
            card_result = await self.db.exec(
                select(Card).where(Card.id == existing_shop_item.card_id)
            )
            card = card_result.first()

        return ShopItemResponse(
            id=existing_shop_item.id,
            name=existing_shop_item.name,
            price=existing_shop_item.price,
            type=existing_shop_item.type,
            card_id=existing_shop_item.card_id,
            card=card,
            rate=existing_shop_item.rate,
            created_at=existing_shop_item.created_at.isoformat(),
            updated_at=existing_shop_item.updated_at.isoformat(),
        )

    async def delete_shop_item(self, shop_item_id: int) -> bool:
        shop_item = await self.get_shop_item(shop_item_id)
        if not shop_item:
            return False

        await self.db.delete(shop_item)
        await self.db.commit()
        return True

    async def purchase_shop_item(self, shop_item_id: int, player_id: int) -> ShopItemResponse:
        """Purchase a shop item for a player.

        Handles currency deduction, inventory addition, and event logging.

        Args:
            shop_item_id: The ID of the shop item to purchase.
            player_id: The ID of the player making the purchase.

        Returns:
            The purchased shop item response.

        Raises:
            HTTPException: If shop item not found, insufficient funds, or item type not supported.
        """
        # Fetch shop item
        result = await self.db.exec(select(ShopItem).where(ShopItem.id == shop_item_id))
        shop_item = result.first()
        if not shop_item:
            raise HTTPException(status_code=404, detail="找不到商店物品")

        # Fetch player
        player_result = await self.db.exec(select(Player).where(Player.id == player_id))
        player = player_result.first()
        if not player:
            raise HTTPException(status_code=404, detail="找不到玩家")

        # Check if player has enough currency
        if player.currency < shop_item.price:
            raise HTTPException(
                status_code=400,
                detail=f"貨幣不足。目前: {player.currency}, 需要: {shop_item.price}",
            )

        # Deduct currency
        player.currency -= shop_item.price
        self.db.add(player)

        # Log currency spending
        spend_event = EventLog(
            player_id=player_id,
            event_type=EventType.SPEND_MONEY,
            context={
                "amount": shop_item.price,
                "reason": f"購買商店物品：{shop_item.name}",
                "shop_item_id": shop_item_id,
            },
        )
        self.db.add(spend_event)

        # Add item to inventory based on type
        if shop_item.type == ShopItemType.CARD:
            if not shop_item.card_id:
                raise HTTPException(status_code=400, detail="卡片商店物品必須要有 card_id")

            # Check if player already has this card in inventory
            inventory_result = await self.db.exec(
                select(Inventory)
                .where(Inventory.player_id == player_id)
                .where(Inventory.card_id == shop_item.card_id)
            )
            existing_inventory = inventory_result.first()

            if existing_inventory:
                # Increment quantity
                existing_inventory.quantity += 1
                self.db.add(existing_inventory)
            else:
                # Create new inventory entry
                inventory = Inventory(player_id=player_id, card_id=shop_item.card_id, quantity=1)
                self.db.add(inventory)

            # Log card acquisition
            obtain_event = EventLog(
                player_id=player_id,
                event_type=EventType.OBTAIN_CARD,
                context={
                    "card_id": shop_item.card_id,
                    "source": "shop_purchase",
                    "shop_item_id": shop_item_id,
                },
            )
            self.db.add(obtain_event)

        elif shop_item.type == ShopItemType.ITEM:
            # Check if player already has this item in inventory
            inventory_result = await self.db.exec(
                select(Inventory)
                .where(Inventory.player_id == player_id)
                .where(Inventory.item_id == shop_item_id)
            )
            existing_inventory = inventory_result.first()

            if existing_inventory:
                # Increment quantity
                existing_inventory.quantity += 1
                self.db.add(existing_inventory)
            else:
                # Create new inventory entry
                inventory = Inventory(player_id=player_id, item_id=shop_item_id, quantity=1)
                self.db.add(inventory)

        await self.db.commit()
        await self.db.refresh(shop_item)

        # Return shop item response with card if applicable
        card = None
        if shop_item.card_id:
            card_result = await self.db.exec(select(Card).where(Card.id == shop_item.card_id))
            card = card_result.first()

        return ShopItemResponse(
            id=shop_item.id,
            name=shop_item.name,
            price=shop_item.price,
            type=shop_item.type,
            rate=shop_item.rate,
            card_id=shop_item.card_id,
            card=card,
            created_at=shop_item.created_at.isoformat(),
            updated_at=shop_item.updated_at.isoformat(),
        )
