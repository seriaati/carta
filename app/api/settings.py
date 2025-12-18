from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core.enums import CardRarity
from app.core.security import require_admin
from app.models.player import Player
from app.schemas.common import APIResponse
from app.schemas.settings import PromptUpdate
from app.services.settings import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/prompt")
async def get_prompt(
    service: Annotated[SettingsService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[str]:
    prompt = await service.get_prompt()
    if prompt is None:
        raise HTTPException(status_code=404, detail="未設定提示詞")
    return APIResponse(data=prompt)


@router.put("/prompt")
async def update_prompt(
    payload: PromptUpdate,
    service: Annotated[SettingsService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[str]:
    updated = await service.set_prompt(payload.prompt)
    return APIResponse(data=updated, message="Prompt updated successfully")


@router.get("/shop-rarities")
async def get_shop_rarities(
    service: Annotated[SettingsService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[dict[str, float]]:
    rarities = await service.get_shop_rarity_rates()
    return APIResponse(data={rarity.value: rate for rarity, rate in rarities.items()})


@router.put("/shop-rarities/{rarity}")
async def update_shop_rarity(
    rarity: CardRarity,
    rate: float,
    service: Annotated[SettingsService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[float]:
    updated_rate = await service.set_shop_rarity_rate(rarity, rate)
    return APIResponse(data=updated_rate, message="Shop rarity rate updated successfully")
