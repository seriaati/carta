from pydantic import BaseModel

from app.core.enums import PvPMode, PvPStatus


class PvPChallengeUpdate(BaseModel):
    challenger_id: int | None = None
    opponent_id: int | None = None
    winner_id: int | None = None
    bet: int | None = None
    status: PvPStatus | None = None
    mode: PvPMode | None = None


class RankingStakeCalculation(BaseModel):
    """Calculation of ranking score stakes before battle."""

    challenger_id: int
    opponent_id: int
    challenger_rank: int
    opponent_rank: int
    challenger_score: int
    opponent_score: int
    challenger_wins_stake: int
    opponent_wins_stake: int
    challenger_can_afford: bool
    opponent_can_afford: bool
