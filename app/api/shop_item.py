from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import require_admin
from app.models.player import Player
from app.models.shop_item import ShopItem
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.shop_item import ShopItemResponse, ShopItemUpdate
from app.services.shop_item import ShopItemService

router = APIRouter(prefix="/shop-items", tags=["shop-items"])


@router.get("/")
async def get_shop_items(
    service: Annotated[ShopItemService, Depends()],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1)] = 10,
) -> PaginatedResponse[Sequence[ShopItemResponse]]:
    shop_items, pagination = await service.get_shop_items(page=page, page_size=page_size)
    return PaginatedResponse[Sequence[ShopItemResponse]](data=shop_items, pagination=pagination)


@router.get("/{shop_item_id}")
async def get_shop_item(
    shop_item_id: int, service: Annotated[ShopItemService, Depends()]
) -> APIResponse[ShopItemResponse]:
    shop_item = await service.get_shop_item(shop_item_id)
    if not shop_item:
        raise HTTPException(status_code=404, detail="找不到商店物品")
    return APIResponse(data=shop_item)


@router.post("/")
async def create_shop_item(
    shop_item: ShopItem,
    service: Annotated[ShopItemService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[ShopItemResponse]:
    created_shop_item = await service.create_shop_item(shop_item)
    return APIResponse(data=created_shop_item, message="Shop item created successfully")


@router.put("/{shop_item_id}")
async def update_shop_item(
    shop_item_id: int,
    shop_item: ShopItemUpdate,
    service: Annotated[ShopItemService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[ShopItemResponse]:
    updated_shop_item = await service.update_shop_item(shop_item_id, shop_item)
    if not updated_shop_item:
        raise HTTPException(status_code=404, detail="找不到商店物品")
    return APIResponse(data=updated_shop_item, message="Shop item updated successfully")


@router.delete("/{shop_item_id}")
async def delete_shop_item(
    shop_item_id: int,
    service: Annotated[ShopItemService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[None]:
    deleted = await service.delete_shop_item(shop_item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="找不到商店物品")
    return APIResponse(message="Shop item deleted successfully")
