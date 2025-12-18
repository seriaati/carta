from pydantic import BaseModel


class DeckCardUpdate(BaseModel):
    player_id: int | None = None
    card_id: int | None = None
    position: int | None = None
