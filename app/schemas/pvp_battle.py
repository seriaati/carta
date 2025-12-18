from pydantic import BaseModel


class CardBattleInfo(BaseModel):
    """Minimal card info for battle - optimized for token efficiency."""

    name: str
    rarity: str
    attack: int
    defense: int
    ability: str


class PlayerBattleInfo(BaseModel):
    """Player's battle data."""

    player_id: int
    cards: list[CardBattleInfo]


class BattleResult(BaseModel):
    """Result from the AI battle judge."""

    winner_id: int
    battle_narrative: str
