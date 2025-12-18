from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import require_admin
from app.models.player import Player
from app.models.trade import Trade
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.trade import TradeUpdate
from app.services.trade import TradeService

router = APIRouter(prefix="/trades", tags=["trades"])


@router.get("/")
async def get_trades(
    service: Annotated[TradeService, Depends()],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1)] = 10,
) -> PaginatedResponse[Sequence[Trade]]:
    trades, pagination = await service.get_trades(page=page, page_size=page_size)
    return PaginatedResponse[Sequence[Trade]](data=trades, pagination=pagination)


@router.get("/{trade_id}")
async def get_trade(
    trade_id: int, service: Annotated[TradeService, Depends()]
) -> APIResponse[Trade]:
    trade = await service.get_trade(trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="找不到交易")
    return APIResponse(data=trade)


# @router.post("/")
# async def create_trade(
#     trade: Trade,
#     service: Annotated[TradeService, Depends()],
#     _admin: Annotated[Player, Depends(require_admin)],
# ) -> APIResponse[Trade]:
#     created_trade = await service.create_trade(trade)
#     return APIResponse(data=created_trade, message="Trade created successfully")


@router.put("/{trade_id}")
async def update_trade(
    trade_id: int,
    trade: TradeUpdate,
    service: Annotated[TradeService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[Trade]:
    updated_trade = await service.update_trade(trade_id, trade)
    if not updated_trade:
        raise HTTPException(status_code=404, detail="找不到交易")
    return APIResponse(data=updated_trade, message="Trade updated successfully")


@router.delete("/{trade_id}")
async def delete_trade(
    trade_id: int,
    service: Annotated[TradeService, Depends()],
    _admin: Annotated[Player, Depends(require_admin)],
) -> APIResponse[None]:
    deleted = await service.delete_trade(trade_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="找不到交易")
    return APIResponse(message="Trade deleted successfully")
