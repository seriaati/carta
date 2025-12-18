from pydantic import BaseModel


class DashboardStats(BaseModel):
    """Dashboard statistics response model."""

    total_players: int
    total_cards: int
    total_card_pools: int
    total_trades: int
    active_trades: int
    total_pvp_challenges: int
    active_pvp_challenges: int
    total_shop_items: int
    total_inventory_items: int
    total_deck_cards: int
