from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import require_admin
from app.models.deck_card import DeckCard
from app.models.player import Player
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.deck_card import DeckCardUpdate
from app.services.deck_card import DeckCardService

router = APIRouter(prefix="/deck-cards", tags=["deck-cards"])


@router.get("/")
async def get_deck_cards(
    service: Annotated[DeckCardService, Depends()],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1)] = 10,
) -> PaginatedResponse[Sequence[DeckCard]]:
    deck_cards, pagination = await service.get_deck_cards(page=page, page_size=page_size)
    return PaginatedResponse(data=deck_cards, pagination=pagination)


@router.get("/{deck_card_id}")
async def get_deck_card(
    deck_card_id: int, service: Annotated[DeckCardService, Depends()]
) -> APIResponse[DeckCard]:
    deck_card = await service.get_deck_card(deck_card_id)
    if not deck_card:
        raise HTTPException(status_code=404, detail="找不到牌組卡片")
    return APIResponse(data=deck_card)


@router.post("/")
async def create_deck_card(
    deck_card: DeckCard,
    service: Annotated[DeckCardService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[DeckCard]:
    created_deck_card = await service.create_deck_card(deck_card)
    return APIResponse(data=created_deck_card, message="Deck card created successfully")


@router.put("/{deck_card_id}")
async def update_deck_card(
    deck_card_id: int,
    deck_card: DeckCardUpdate,
    service: Annotated[DeckCardService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[DeckCard]:
    updated_deck_card = await service.update_deck_card(deck_card_id, deck_card)
    if not updated_deck_card:
        raise HTTPException(status_code=404, detail="找不到牌組卡片")
    return APIResponse(data=updated_deck_card, message="Deck card updated successfully")


@router.delete("/{deck_card_id}")
async def delete_deck_card(
    deck_card_id: int,
    service: Annotated[DeckCardService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[None]:
    deleted = await service.delete_deck_card(deck_card_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="找不到牌組卡片")
    return APIResponse(message="Deck card deleted successfully")
