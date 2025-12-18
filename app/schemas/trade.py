from pydantic import BaseModel, ValidationInfo, field_validator

from app.core.enums import TradeStatus


class TradeCreate(BaseModel):
    """Schema for creating a new trade request."""

    receiver_id: int
    offered_card_id: int
    requested_card_id: int | None = None
    price: int | None = None

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            msg = "Price must be non-negative"
            raise ValueError(msg)
        return v

    @field_validator("requested_card_id", "price")
    @classmethod
    def validate_card_or_price(cls, v: int | None, info: ValidationInfo) -> int | None:
        """Ensure either requested_card_id or price is provided, but not both."""
        values = info.data
        if "requested_card_id" in values:
            requested_card = values.get("requested_card_id")
            price = v if info.field_name == "price" else values.get("price")

            if requested_card is None and price is None:
                msg = "Either requested_card_id or price must be provided"
                raise ValueError(msg)
            if requested_card is not None and price is not None:
                msg = "Cannot request both a card and money"
                raise ValueError(msg)
        return v


class TradeResponse(BaseModel):
    """Schema for responding to a trade (accept/reject)."""

    accepted: bool


class TradeUpdate(BaseModel):
    """Schema for updating trade fields (admin only)."""

    proposer_id: int | None = None
    receiver_id: int | None = None
    offered_card_id: int | None = None
    requested_card_id: int | None = None
    price: int | None = None
    status: TradeStatus | None = None
