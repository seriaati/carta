import sqlmodel

from ._base import BaseModel


class DeckCard(BaseModel, table=True):
    __tablename__: str = "deck_cards"

    id: int = sqlmodel.Field(primary_key=True, index=True, default=None)
    player_id: int = sqlmodel.Field(
        foreign_key="players.id", index=True, sa_type=sqlmodel.BigInteger
    )
    card_id: int = sqlmodel.Field(foreign_key="cards.id", index=True)
    position: int = sqlmodel.Field(ge=1, le=6)
