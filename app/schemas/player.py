from pydantic import BaseModel, Field

from app.core.enums import CardRarity


class PlayerUpdate(BaseModel):
    # Player model only has id field, which shouldn't be changeable
    # So this is empty but kept for consistency
    pass


class CurrencyAdjustment(BaseModel):
    """Schema for adjusting player currency (increase or decrease)."""

    amount: int = Field(gt=0, description="Amount to adjust (must be positive)")
    reason: str = Field(min_length=1, max_length=255, description="Reason for adjustment")


class CurrencySet(BaseModel):
    """Schema for setting player currency to a specific amount."""

    amount: int = Field(ge=0, description="New currency amount (must be non-negative)")
    reason: str = Field(min_length=1, max_length=255, description="Reason for setting currency")


class CardStatistics(BaseModel):
    """Schema for player card statistics."""

    total_owned_cards: int = Field(description="Total number of cards owned by the player")
    cards_per_rarity: dict[CardRarity, int] = Field(
        description="Number of cards owned per rarity level"
    )
