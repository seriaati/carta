from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import require_admin
from app.models.player import Player
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.player import CurrencyAdjustment, CurrencySet, PlayerUpdate
from app.services.player import PlayerService

router = APIRouter(prefix="/players", tags=["players"])


@router.get("/")
async def get_players(
    service: Annotated[PlayerService, Depends()],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1)] = 10,
) -> PaginatedResponse[Sequence[Player]]:
    players, pagination = await service.get_players(page=page, page_size=page_size)
    return PaginatedResponse(data=players, pagination=pagination)


@router.get("/{player_id}")
async def get_player(
    player_id: int, service: Annotated[PlayerService, Depends()]
) -> APIResponse[Player]:
    player = await service.get_player(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="找不到玩家")
    return APIResponse(data=player)


@router.post("/")
async def create_player(
    player: Player,
    service: Annotated[PlayerService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[Player]:
    created_player = await service.create_player(player)
    return APIResponse(data=created_player, message="Player created successfully")


@router.put("/{player_id}")
async def update_player(
    player_id: int,
    player: PlayerUpdate,
    service: Annotated[PlayerService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[Player]:
    updated_player = await service.update_player(player_id, player)
    if not updated_player:
        raise HTTPException(status_code=404, detail="找不到玩家")
    return APIResponse(data=updated_player, message="Player updated successfully")


@router.delete("/{player_id}")
async def delete_player(
    player_id: int,
    service: Annotated[PlayerService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[None]:
    deleted = await service.delete_player(player_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="找不到玩家")
    return APIResponse(message="Player deleted successfully")


@router.post("/{player_id}/currency/increase")
async def increase_currency(
    player_id: int,
    adjustment: CurrencyAdjustment,
    service: Annotated[PlayerService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[Player]:
    """Increase a player's currency (admin only)."""
    player = await service.increase_currency(player_id, adjustment.amount, adjustment.reason)
    return APIResponse(data=player, message=f"Increased currency by {adjustment.amount}")


@router.post("/{player_id}/currency/decrease")
async def decrease_currency(
    player_id: int,
    adjustment: CurrencyAdjustment,
    service: Annotated[PlayerService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[Player]:
    """Decrease a player's currency (admin only)."""
    player = await service.decrease_currency(player_id, adjustment.amount, adjustment.reason)
    return APIResponse(data=player, message=f"Decreased currency by {adjustment.amount}")


@router.post("/{player_id}/currency/set")
async def set_currency(
    player_id: int,
    currency_set: CurrencySet,
    service: Annotated[PlayerService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[Player]:
    """Set a player's currency to a specific amount (admin only)."""
    player = await service.set_currency(player_id, currency_set.amount, currency_set.reason)
    return APIResponse(data=player, message=f"Set currency to {currency_set.amount}")
