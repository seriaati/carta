from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import require_admin
from app.models.card_pool_card import CardPoolCard
from app.models.player import Player
from app.schemas.card_pool_card import CardPoolCardUpdate
from app.schemas.common import APIResponse, PaginatedResponse
from app.services.card_pool_card import CardPoolCardService

router = APIRouter(prefix="/card-pool-cards", tags=["card-pool-cards"])


@router.get("/")
async def get_card_pool_cards(
    service: Annotated[CardPoolCardService, Depends()],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1)] = 10,
) -> PaginatedResponse[Sequence[CardPoolCard]]:
    card_pool_cards, pagination = await service.get_card_pool_cards(page=page, page_size=page_size)
    return PaginatedResponse(data=card_pool_cards, pagination=pagination)


@router.get("/{card_pool_card_id}")
async def get_card_pool_card(
    card_pool_card_id: int, service: Annotated[CardPoolCardService, Depends()]
) -> APIResponse[CardPoolCard]:
    card_pool_card = await service.get_card_pool_card(card_pool_card_id)
    if not card_pool_card:
        raise HTTPException(status_code=404, detail="找不到卡池卡片")
    return APIResponse(data=card_pool_card)


@router.post("/")
async def create_card_pool_card(
    card_pool_card: CardPoolCard,
    service: Annotated[CardPoolCardService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[CardPoolCard]:
    created_card_pool_card = await service.create_card_pool_card(card_pool_card)
    return APIResponse(data=created_card_pool_card, message="Card pool card created successfully")


@router.put("/{card_pool_card_id}")
async def update_card_pool_card(
    card_pool_card_id: int,
    card_pool_card: CardPoolCardUpdate,
    service: Annotated[CardPoolCardService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[CardPoolCard]:
    updated_card_pool_card = await service.update_card_pool_card(card_pool_card_id, card_pool_card)
    if not updated_card_pool_card:
        raise HTTPException(status_code=404, detail="找不到卡池卡片")
    return APIResponse(data=updated_card_pool_card, message="Card pool card updated successfully")


@router.delete("/{card_pool_card_id}")
async def delete_card_pool_card(
    card_pool_card_id: int,
    service: Annotated[CardPoolCardService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[None]:
    deleted = await service.delete_card_pool_card(card_pool_card_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="找不到卡池卡片")
    return APIResponse(message="Card pool card deleted successfully")
