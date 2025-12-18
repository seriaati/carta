from pydantic import BaseModel

from app.models.card import Card


class CardPoolUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class CardWithProbability(BaseModel):
    """Card with its probability in a card pool."""

    card_pool_card_id: int
    card: Card
    probability: float
