from pydantic import BaseModel


class CardPoolCardUpdate(BaseModel):
    pool_id: int | None = None
    card_id: int | None = None
    probability: float | None = None
