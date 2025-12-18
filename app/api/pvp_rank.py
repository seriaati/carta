from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import require_admin
from app.models.player import Player
from app.models.pvp_rank import PvPRank
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.pvp_rank import PvPRankUpdate
from app.services.pvp_rank import PvPRankService

router = APIRouter(prefix="/pvp-ranks", tags=["pvp-ranks"])


@router.get("/")
async def get_pvp_ranks(
    service: Annotated[PvPRankService, Depends()],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1)] = 10,
) -> PaginatedResponse[Sequence[PvPRank]]:
    pvp_ranks, pagination = await service.get_pvp_ranks(page=page, page_size=page_size)
    return PaginatedResponse(data=pvp_ranks, pagination=pagination)


@router.get("/{pvp_rank_id}")
async def get_pvp_rank(
    pvp_rank_id: int, service: Annotated[PvPRankService, Depends()]
) -> APIResponse[PvPRank]:
    pvp_rank = await service.get_pvp_rank(pvp_rank_id)
    if not pvp_rank:
        raise HTTPException(status_code=404, detail="找不到 PvP 等級")
    return APIResponse(data=pvp_rank)


@router.post("/")
async def create_pvp_rank(
    pvp_rank: PvPRank,
    service: Annotated[PvPRankService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[PvPRank]:
    created_pvp_rank = await service.create_pvp_rank(pvp_rank)
    return APIResponse(data=created_pvp_rank, message="PvP rank created successfully")


@router.put("/{pvp_rank_id}")
async def update_pvp_rank(
    pvp_rank_id: int,
    pvp_rank: PvPRankUpdate,
    service: Annotated[PvPRankService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[PvPRank]:
    updated_pvp_rank = await service.update_pvp_rank(pvp_rank_id, pvp_rank)
    if not updated_pvp_rank:
        raise HTTPException(status_code=404, detail="找不到 PvP 等級")
    return APIResponse(data=updated_pvp_rank, message="PvP rank updated successfully")


@router.delete("/{pvp_rank_id}")
async def delete_pvp_rank(
    pvp_rank_id: int,
    service: Annotated[PvPRankService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[None]:
    deleted = await service.delete_pvp_rank(pvp_rank_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="找不到 PvP 等級")
    return APIResponse(message="PvP rank deleted successfully")
