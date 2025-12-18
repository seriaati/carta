from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import require_admin
from app.models.card_pool import CardPool
from app.models.player import Player
from app.schemas.card_pool import CardPoolUpdate, CardWithProbability
from app.schemas.common import APIResponse, PaginatedResponse
from app.services.card_pool import CardPoolService

router = APIRouter(prefix="/card-pools", tags=["card-pools"])


@router.get("/")
async def get_card_pools(
    service: Annotated[CardPoolService, Depends()],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1)] = 10,
) -> PaginatedResponse[Sequence[CardPool]]:
    card_pools, pagination = await service.get_card_pools(page=page, page_size=page_size)
    return PaginatedResponse(data=card_pools, pagination=pagination)


@router.get("/{card_pool_id}")
async def get_card_pool(
    card_pool_id: int, service: Annotated[CardPoolService, Depends()]
) -> APIResponse[CardPool]:
    card_pool = await service.get_card_pool(card_pool_id)
    if not card_pool:
        raise HTTPException(status_code=404, detail="找不到卡池")
    return APIResponse(data=card_pool)


@router.post("/")
async def create_card_pool(
    card_pool: CardPool,
    service: Annotated[CardPoolService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[CardPool]:
    created_card_pool = await service.create_card_pool(card_pool)
    return APIResponse(data=created_card_pool, message="Card pool created successfully")


@router.put("/{card_pool_id}")
async def update_card_pool(
    card_pool_id: int,
    card_pool: CardPoolUpdate,
    service: Annotated[CardPoolService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[CardPool]:
    updated_card_pool = await service.update_card_pool(card_pool_id, card_pool)
    if not updated_card_pool:
        raise HTTPException(status_code=404, detail="找不到卡池")
    return APIResponse(data=updated_card_pool, message="Card pool updated successfully")


@router.delete("/{card_pool_id}")
async def delete_card_pool(
    card_pool_id: int,
    service: Annotated[CardPoolService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[None]:
    deleted = await service.delete_card_pool(card_pool_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="找不到卡池")
    return APIResponse(message="Card pool deleted successfully")


@router.get("/{card_pool_id}/cards")
async def get_card_pool_cards(
    card_pool_id: int, service: Annotated[CardPoolService, Depends()]
) -> APIResponse[list[CardWithProbability]]:
    """Get all cards in a card pool with their probabilities."""
    card_pool = await service.get_card_pool(card_pool_id)
    if not card_pool:
        raise HTTPException(status_code=404, detail="找不到卡池")

    cards_with_probs = await service.get_card_pool_cards(card_pool_id)
    data = [
        CardWithProbability(card_pool_card_id=cpc_id, card=card, probability=prob)
        for cpc_id, card, prob in cards_with_probs
    ]
    return APIResponse(data=data)
