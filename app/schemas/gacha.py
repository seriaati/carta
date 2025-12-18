from pydantic import BaseModel, Field

from app.core.enums import CardRarity


class GachaPullRequest(BaseModel):
    """Request to pull from a gacha card pool."""

    pool_id: int = Field(description="ID of the card pool to pull from")
    count: int = Field(default=1, ge=1, le=10, description="Number of pulls (1 or 10)")


class GachaPullResult(BaseModel):
    """Result of a single gacha pull."""

    card_id: int
    card_name: str
    card_rarity: CardRarity
    was_pity: bool


class GachaPullResponse(BaseModel):
    """Response containing all pull results."""

    pulls: list[GachaPullResult]
    remaining_currency: int
    current_pity: int


class GachaPityResponse(BaseModel):
    """Response for checking pity count."""

    pool_id: int
    pool_name: str
    current_pity: int
    max_pity: int = 1000
