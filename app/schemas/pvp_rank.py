from datetime import datetime

from pydantic import BaseModel


class PvPRankUpdate(BaseModel):
    player_id: int | None = None
    points: int | None = None
    week: int | None = None
    score_updated_at: datetime | None = None
    daily_plays: int | None = None
    last_play_date: datetime | None = None


class LeaderboardEntry(BaseModel):
    """Leaderboard entry with rank and player info."""

    rank: int
    player_id: int
    points: int
    score_updated_at: datetime
