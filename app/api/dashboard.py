from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security import require_admin
from app.schemas.common import APIResponse
from app.schemas.dashboard import DashboardStats
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", dependencies=[Depends(require_admin)])
async def get_dashboard_stats(
    service: Annotated[DashboardService, Depends()],
) -> APIResponse[DashboardStats]:
    """
    Get comprehensive dashboard statistics.

    Requires admin authentication.

    Returns statistics including:
    - Total players
    - Total cards
    - Total card pools
    - Total trades (and active trades)
    - Total PvP challenges (and active challenges)
    - Total shop items
    - Total inventory items
    - Total deck cards
    """
    stats = await service.get_dashboard_stats()
    return APIResponse(data=stats)
