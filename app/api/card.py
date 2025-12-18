from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.enums import CardSortField, SortOrder
from app.core.security import require_admin
from app.models.card import Card
from app.models.player import Player
from app.schemas.card import CardCreate, CardListParams, CardUpdate
from app.schemas.common import APIResponse, PaginatedResponse
from app.services.card import CardService

router = APIRouter(prefix="/cards", tags=["cards"])


@router.get("/")
async def get_cards(  # noqa: PLR0913, PLR0917
    service: Annotated[CardService, Depends()],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1)] = 10,
    search_name: Annotated[
        str | None, Query(description="Search cards by name (partial match)")
    ] = None,
    search_id: Annotated[int | None, Query(description="Search card by exact ID")] = None,
    sort_by: Annotated[CardSortField, Query(description="Field to sort by")] = CardSortField.ID,
    sort_order: Annotated[SortOrder, Query(description="Sort order")] = SortOrder.ASC,
) -> PaginatedResponse[Sequence[Card]]:
    params = CardListParams(
        search_name=search_name, search_id=search_id, sort_by=sort_by, sort_order=sort_order
    )
    cards, pagination = await service.get_cards(page=page, page_size=page_size, params=params)
    return PaginatedResponse(data=cards, pagination=pagination)


@router.get("/{card_id}")
async def get_card(card_id: int, service: Annotated[CardService, Depends()]) -> APIResponse[Card]:
    card = await service.get_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="找不到卡片")
    return APIResponse(data=card)


@router.post("/")
async def create_card(
    card: CardCreate,
    service: Annotated[CardService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[Card]:
    created_card = await service.create_card(card)
    return APIResponse(data=created_card, message="Card created successfully")


@router.put("/{card_id}")
async def update_card(
    card_id: int,
    card: CardUpdate,
    service: Annotated[CardService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[Card]:
    updated_card = await service.update_card(card_id, card)
    if not updated_card:
        raise HTTPException(status_code=404, detail="找不到卡片")
    return APIResponse(data=updated_card, message="Card updated successfully")


@router.delete("/{card_id}")
async def delete_card(
    card_id: int,
    service: Annotated[CardService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[None]:
    deleted = await service.delete_card(card_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="找不到卡片")
    return APIResponse(message="Card deleted successfully")
