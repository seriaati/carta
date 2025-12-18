from collections.abc import Sequence
from contextlib import suppress
from typing import Annotated

from fastapi import Depends
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_db
from app.core.enums import SortOrder
from app.models.card import Card
from app.schemas.card import CardCreate, CardListParams, CardUpdate
from app.schemas.common import PaginationData
from app.utils.cdn import delete_image_from_cdn, upload_image_to_cdn


class CardService:
    def __init__(self, db: Annotated[AsyncSession, Depends(get_db)]) -> None:
        self.db = db

    async def get_cards(
        self, *, page: int, page_size: int, params: CardListParams
    ) -> tuple[Sequence[Card], PaginationData]:
        offset = (page - 1) * page_size

        # Build base query with filters
        query = select(Card)

        # Apply search filters
        if params.search_name:
            query = query.where(col(Card.name).ilike(f"%{params.search_name}%"))
        if params.search_id is not None:
            query = query.where(Card.id == params.search_id)

        # Get total items with filters applied
        total_items_result = await self.db.exec(query)
        total_items = len(total_items_result.all())

        total_pages = (total_items + page_size - 1) // page_size

        # Apply sorting
        sort_column = getattr(Card, params.sort_by.value)
        if params.sort_order == SortOrder.DESC:
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Apply pagination
        query = query.offset(offset).limit(page_size)
        result = await self.db.exec(query)
        cards = result.all()

        pagination = PaginationData(
            page=page, page_size=page_size, total_items=total_items, total_pages=total_pages
        )

        return cards, pagination

    async def get_cards_by_name(self, name: str) -> Sequence[Card]:
        query = select(Card).where(col(Card.name).ilike(f"%{name}%"))
        result = await self.db.exec(query)
        return result.all()

    async def get_card(self, card_id: int) -> Card | None:
        result = await self.db.exec(select(Card).where(Card.id == card_id))
        return result.first()

    async def create_card(self, card_data: CardCreate) -> Card:
        # Upload image to CDN
        image_url = await upload_image_to_cdn(card_data.image)

        # Create card with image URL
        card = Card(
            name=card_data.name,
            image_url=image_url,
            description=card_data.description,
            rarity=card_data.rarity,
            attack=card_data.attack,
            defense=card_data.defense,
            price=card_data.price,
        )

        self.db.add(card)
        await self.db.commit()
        await self.db.refresh(card)
        return card

    async def update_card(self, card_id: int, card_data: CardUpdate) -> Card | None:
        existing_card = await self.get_card(card_id)
        if not existing_card:
            return None

        # If image is provided, upload to CDN and delete old image
        update_dict = card_data.model_dump(exclude_unset=True)
        if "image" in update_dict and update_dict["image"] is not None:
            # Delete old image from CDN if it exists
            if existing_card.image_url:
                # Suppress errors if image deletion fails (might already be deleted)
                with suppress(Exception):
                    await delete_image_from_cdn(existing_card.image_url)

            # Upload new image
            image_url = await upload_image_to_cdn(update_dict["image"])
            update_dict["image_url"] = image_url
            del update_dict["image"]  # Remove the string field

        existing_card.sqlmodel_update(update_dict)
        self.db.add(existing_card)
        await self.db.commit()
        await self.db.refresh(existing_card)
        return existing_card

    async def delete_card(self, card_id: int) -> bool:
        card = await self.get_card(card_id)
        if not card:
            return False

        # Delete image from CDN if it exists
        if card.image_url:
            # Suppress errors if image deletion fails (might already be deleted)
            with suppress(Exception):
                await delete_image_from_cdn(card.image_url)

        await self.db.delete(card)
        await self.db.commit()
        return True
