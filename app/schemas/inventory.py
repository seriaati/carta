from pydantic import BaseModel


class InventoryUpdate(BaseModel):
    player_id: int | None = None
    item_id: int | None = None
    card_id: int | None = None
    quantity: int | None = None


class SellCardResponse(BaseModel):
    """Response schema for selling cards."""

    card_id: int
    card_name: str
    quantity_sold: int
    unit_price: int
    total_value: int
    new_currency_balance: int
