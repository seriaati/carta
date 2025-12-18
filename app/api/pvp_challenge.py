from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import require_admin
from app.models.player import Player
from app.models.pvp_challenge import PvPChallenge
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.pvp_challenge import PvPChallengeUpdate
from app.services.pvp_challenge import PvPChallengeService

router = APIRouter(prefix="/pvp-challenges", tags=["pvp-challenges"])


@router.get("/")
async def get_pvp_challenges(
    service: Annotated[PvPChallengeService, Depends()],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1)] = 10,
) -> PaginatedResponse[Sequence[PvPChallenge]]:
    pvp_challenges, pagination = await service.get_pvp_challenges(page=page, page_size=page_size)
    return PaginatedResponse(data=pvp_challenges, pagination=pagination)


@router.get("/{pvp_challenge_id}")
async def get_pvp_challenge(
    pvp_challenge_id: int, service: Annotated[PvPChallengeService, Depends()]
) -> APIResponse[PvPChallenge]:
    pvp_challenge = await service.get_pvp_challenge(pvp_challenge_id)
    if not pvp_challenge:
        raise HTTPException(status_code=404, detail="找不到 PvP 挑戰")
    return APIResponse(data=pvp_challenge)


@router.post("/")
async def create_pvp_challenge(
    pvp_challenge: PvPChallenge,
    service: Annotated[PvPChallengeService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[PvPChallenge]:
    created_pvp_challenge = await service.create_pvp_challenge(pvp_challenge)
    return APIResponse(data=created_pvp_challenge, message="PvP challenge created successfully")


@router.put("/{pvp_challenge_id}")
async def update_pvp_challenge(
    pvp_challenge_id: int,
    pvp_challenge: PvPChallengeUpdate,
    service: Annotated[PvPChallengeService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[PvPChallenge]:
    updated_pvp_challenge = await service.update_pvp_challenge(pvp_challenge_id, pvp_challenge)
    if not updated_pvp_challenge:
        raise HTTPException(status_code=404, detail="找不到 PvP 挑戰")
    return APIResponse(data=updated_pvp_challenge, message="PvP challenge updated successfully")


@router.delete("/{pvp_challenge_id}")
async def delete_pvp_challenge(
    pvp_challenge_id: int,
    service: Annotated[PvPChallengeService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[None]:
    deleted = await service.delete_pvp_challenge(pvp_challenge_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="找不到 PvP 挑戰")
    return APIResponse(message="PvP challenge deleted successfully")
