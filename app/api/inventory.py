from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import require_admin
from app.models.inventory import Inventory
from app.models.player import Player
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.inventory import InventoryUpdate
from app.services.inventory import InventoryService

router = APIRouter(prefix="/inventories", tags=["inventories"])


@router.get("/")
async def get_inventories(
    service: Annotated[InventoryService, Depends()],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1)] = 10,
) -> PaginatedResponse[Sequence[Inventory]]:
    inventories, pagination = await service.get_inventories(page=page, page_size=page_size)
    return PaginatedResponse(data=inventories, pagination=pagination)


@router.get("/{inventory_id}")
async def get_inventory(
    inventory_id: int, service: Annotated[InventoryService, Depends()]
) -> APIResponse[Inventory]:
    inventory = await service.get_inventory(inventory_id)
    if not inventory:
        raise HTTPException(status_code=404, detail="找不到庫存")
    return APIResponse(data=inventory)


@router.post("/")
async def create_inventory(
    inventory: Inventory,
    service: Annotated[InventoryService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[Inventory]:
    created_inventory = await service.create_inventory(inventory)
    return APIResponse(data=created_inventory, message="Inventory created successfully")


@router.put("/{inventory_id}")
async def update_inventory(
    inventory_id: int,
    inventory: InventoryUpdate,
    service: Annotated[InventoryService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[Inventory]:
    updated_inventory = await service.update_inventory(inventory_id, inventory)
    if not updated_inventory:
        raise HTTPException(status_code=404, detail="找不到庫存")
    return APIResponse(data=updated_inventory, message="Inventory updated successfully")


@router.delete("/{inventory_id}")
async def delete_inventory(
    inventory_id: int,
    service: Annotated[InventoryService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[None]:
    deleted = await service.delete_inventory(inventory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="找不到庫存")
    return APIResponse(message="Inventory deleted successfully")
