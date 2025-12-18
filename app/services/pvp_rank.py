import math
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends
from sqlmodel import col, desc, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_db
from app.core.enums import EventType
from app.models.event_log import EventLog
from app.models.player import Player
from app.models.pvp_rank import PvPRank
from app.schemas.common import PaginationData
from app.schemas.pvp_challenge import RankingStakeCalculation
from app.schemas.pvp_rank import LeaderboardEntry, PvPRankUpdate
from app.utils.misc import get_utc8_now


class PvPRankService:  # noqa: PLR0904
    def __init__(self, db: Annotated[AsyncSession, Depends(get_db)]) -> None:
        self.db = db

    @staticmethod
    def get_current_week() -> int:
        """Calculate current week number based on UTC+8 Monday 00:00."""
        now = datetime.now(UTC) + timedelta(hours=8)
        # Get the Monday of current week
        monday = now - timedelta(days=now.weekday())
        # Calculate weeks since epoch
        return int(monday.timestamp() / (7 * 24 * 3600))

    @staticmethod
    def is_new_day(last_date: datetime | None) -> bool:
        """Check if it's a new day (UTC+8)."""
        if last_date is None:
            return True
        now = get_utc8_now()
        last = last_date + timedelta(hours=8) if last_date.tzinfo is None else last_date
        return now.date() > last.date()

    async def get_pvp_ranks(
        self, *, page: int, page_size: int
    ) -> tuple[Sequence[PvPRank], PaginationData]:
        offset = (page - 1) * page_size

        total_items_result = await self.db.exec(select(PvPRank))
        total_items = len(total_items_result.all())

        total_pages = (total_items + page_size - 1) // page_size

        result = await self.db.exec(select(PvPRank).offset(offset).limit(page_size))
        pvp_ranks = result.all()

        pagination = PaginationData(
            page=page, page_size=page_size, total_items=total_items, total_pages=total_pages
        )

        return pvp_ranks, pagination

    async def get_pvp_rank(self, pvp_rank_id: int) -> PvPRank | None:
        result = await self.db.exec(select(PvPRank).where(PvPRank.id == pvp_rank_id))
        return result.first()

    async def get_player_rank(self, player_id: int, week: int | None = None) -> PvPRank:
        """Get or create a player's rank record for the current or specified week."""
        if week is None:
            week = self.get_current_week()

        result = await self.db.exec(
            select(PvPRank).where(col(PvPRank.player_id) == player_id, col(PvPRank.week) == week)
        )
        rank = result.first()

        if rank is None:
            # Create new rank record with default values
            rank = PvPRank(
                player_id=player_id,
                week=week,
                points=50,
                score_updated_at=get_utc8_now(),
                daily_plays=0,
            )
            self.db.add(rank)
            await self.db.commit()
            await self.db.refresh(rank)

        return rank

    async def get_leaderboard(
        self, week: int | None = None, limit: int = 100
    ) -> list[LeaderboardEntry]:
        """Get ranked leaderboard for a week, sorted by points desc then score_updated_at asc."""
        if week is None:
            week = self.get_current_week()

        result = await self.db.exec(
            select(PvPRank)
            .where(col(PvPRank.week) == week)
            .order_by(desc(col(PvPRank.points)), col(PvPRank.score_updated_at))
            .limit(limit)
        )
        ranks = result.all()

        return [
            LeaderboardEntry(
                rank=idx + 1,
                player_id=rank.player_id,
                points=rank.points,
                score_updated_at=rank.score_updated_at,
            )
            for idx, rank in enumerate(ranks)
        ]

    async def get_top_100_leaderboard(self, week: int | None = None) -> list[LeaderboardEntry]:
        """Get the top 100 players on the leaderboard."""
        return await self.get_leaderboard(week=week, limit=100)

    async def get_leaderboard_near_player(
        self, player_id: int, week: int | None = None, context_size: int = 50
    ) -> list[LeaderboardEntry]:
        """Get leaderboard entries near a player's position.

        Returns entries from (player_rank - context_size) to (player_rank + context_size),
        with the player in the middle. Total entries: context_size * 2 + 1 (default 101).

        Args:
            player_id: The player to center the results around
            week: Week number (defaults to current week)
            context_size: Number of entries above and below the player (default 50)

        Returns:
            List of LeaderboardEntry objects centered around the player
        """
        if week is None:
            week = self.get_current_week()

        # Get player's rank position
        player_rank = await self.get_player_leaderboard_rank(player_id, week)

        # Calculate offset (how many entries to skip)
        # offset = max(0, player_rank - context_size - 1)
        start_rank = max(1, player_rank - context_size)
        offset = start_rank - 1

        # Calculate limit (total entries to fetch)
        total_entries = context_size * 2 + 1

        # Get the entries around the player
        result = await self.db.exec(
            select(PvPRank)
            .where(col(PvPRank.week) == week)
            .order_by(desc(col(PvPRank.points)), col(PvPRank.score_updated_at))
            .offset(offset)
            .limit(total_entries)
        )
        ranks = result.all()

        return [
            LeaderboardEntry(
                rank=start_rank + idx,
                player_id=rank.player_id,
                points=rank.points,
                score_updated_at=rank.score_updated_at,
            )
            for idx, rank in enumerate(ranks)
        ]

    async def get_player_leaderboard_rank(self, player_id: int, week: int | None = None) -> int:
        """Get a player's rank position in the leaderboard (1-indexed)."""
        if week is None:
            week = self.get_current_week()

        player_rank = await self.get_player_rank(player_id, week)

        # Count how many players have higher points or same points but earlier timestamp
        result = await self.db.exec(
            select(func.count())
            .select_from(PvPRank)
            .where(
                col(PvPRank.week) == week,
                (
                    (col(PvPRank.points) > player_rank.points)
                    | (
                        (col(PvPRank.points) == player_rank.points)
                        & (col(PvPRank.score_updated_at) < player_rank.score_updated_at)
                    )
                ),
            )
        )
        higher_count = result.one()
        return higher_count + 1

    def calculate_score_change(self, winner_rank: int, loser_rank: int, loser_score: int) -> int:
        """Calculate how many points the winner gets from the loser.

        Args:
            winner_rank: Winner's leaderboard position (1-indexed)
            loser_rank: Loser's leaderboard position (1-indexed)
            loser_score: Loser's current score

        Returns:
            Points to transfer from loser to winner
        """
        rank_diff = loser_rank - winner_rank

        if rank_diff > 50:
            # Winner is 50+ ranks higher (better), only gets 1 point
            score_change = 1
        elif rank_diff > 0:
            # Loser is higher ranked (better), winner gets up to 50 points
            score_change = min(rank_diff, 50)
        else:
            # Winner is higher/equal ranked, gets reduced points
            # Formula: (50 - abs(rank_diff)) / 2, rounded up
            score_change = math.ceil((50 - abs(rank_diff)) / 2)

        # Cap by loser's available score
        return min(score_change, loser_score)

    async def calculate_ranking_stakes(
        self, challenger_id: int, opponent_id: int
    ) -> RankingStakeCalculation:
        """Calculate what's at stake for both players before a ranked battle."""
        week = self.get_current_week()

        challenger_rank_obj = await self.get_player_rank(challenger_id, week)
        opponent_rank_obj = await self.get_player_rank(opponent_id, week)

        challenger_rank = await self.get_player_leaderboard_rank(challenger_id, week)
        opponent_rank = await self.get_player_leaderboard_rank(opponent_id, week)

        # Calculate what each player wins if they win
        challenger_wins_stake = self.calculate_score_change(
            challenger_rank, opponent_rank, opponent_rank_obj.points
        )
        opponent_wins_stake = self.calculate_score_change(
            opponent_rank, challenger_rank, challenger_rank_obj.points
        )

        return RankingStakeCalculation(
            challenger_id=challenger_id,
            opponent_id=opponent_id,
            challenger_rank=challenger_rank,
            opponent_rank=opponent_rank,
            challenger_score=challenger_rank_obj.points,
            opponent_score=opponent_rank_obj.points,
            challenger_wins_stake=challenger_wins_stake,
            opponent_wins_stake=opponent_wins_stake,
            challenger_can_afford=challenger_rank_obj.points >= opponent_wins_stake,
            opponent_can_afford=opponent_rank_obj.points >= challenger_wins_stake,
        )

    async def check_daily_limit_and_get_fee(self, player_id: int) -> int:
        """Check if player can play and return the fee amount.

        Fee structure: doubles every 5 plays starting from 500.
        - Plays 0-9: 0 (free)
        - Plays 10-14: 500
        - Plays 15-19: 1000
        - Plays 20-24: 2000
        - Plays 25-29: 4000
        - And so on, doubling every 5 plays

        Returns:
            Fee amount (0 if within first 10 free plays)
        """
        week = self.get_current_week()
        rank = await self.get_player_rank(player_id, week)

        # Reset daily plays if it's a new day
        if self.is_new_day(rank.last_play_date):
            rank.daily_plays = 0
            rank.last_play_date = get_utc8_now()
            self.db.add(rank)
            await self.db.commit()
            await self.db.refresh(rank)

        plays = rank.daily_plays

        # Calculate fee: free for first 10, then 500 * 2^((plays-10)//5)
        if plays < 10:
            fee = 0
        else:
            # Calculate which tier (0-indexed): 10-14 is tier 0, 15-19 is tier 1, etc.
            tier = (plays - 10) // 5
            fee = 500 * (2**tier)

        return fee

    async def charge_play_fee(self, player_id: int, fee: int) -> None:
        """Charge a player for ranked play and log the event."""
        if fee == 0:
            return

        result = await self.db.exec(select(Player).where(Player.id == player_id))
        player = result.first()

        if not player or player.currency < fee:
            msg = f"玩家 {player_id} 無法支付參賽費用 {fee}"
            raise ValueError(msg)

        player.currency -= fee
        self.db.add(player)

        # Log the fee payment
        event_log = EventLog(
            player_id=player_id,
            event_type=EventType.RANKED_PLAY_FEE,
            context={"fee": fee, "plays": (await self.get_player_rank(player_id)).daily_plays},
        )
        self.db.add(event_log)

        await self.db.commit()

    async def increment_daily_plays(self, player_id: int) -> None:
        """Increment a player's daily play counter."""
        week = self.get_current_week()
        rank = await self.get_player_rank(player_id, week)

        rank.daily_plays += 1
        rank.last_play_date = get_utc8_now()
        self.db.add(rank)
        await self.db.commit()

    async def check_daily_bet_limit(self, player_id: int, bet_amount: int) -> bool:
        """Check if player can bet this amount without exceeding daily limit of 1,000,000.

        Returns:
            True if player can bet this amount, False otherwise
        """
        week = self.get_current_week()
        rank = await self.get_player_rank(player_id, week)

        # Reset daily bet amount if it's a new day
        if self.is_new_day(rank.last_bet_date):
            rank.daily_bet_amount = 0
            rank.last_bet_date = get_utc8_now()
            self.db.add(rank)
            await self.db.commit()
            await self.db.refresh(rank)

        # Check if adding this bet would exceed the daily limit
        return (rank.daily_bet_amount + bet_amount) <= 1_000_000

    async def increment_daily_bet_amount(self, player_id: int, bet_amount: int) -> None:
        """Increment a player's daily bet amount."""
        week = self.get_current_week()
        rank = await self.get_player_rank(player_id, week)

        rank.daily_bet_amount += bet_amount
        rank.last_bet_date = get_utc8_now()
        self.db.add(rank)
        await self.db.commit()

    async def validate_player_can_bet(self, player_id: int, bet_amount: int) -> tuple[bool, str]:
        """Validate if a player can place a bet.

        Checks:
        1. Bet amount is within allowed range (1 to 100,000)
        2. Player has enough currency
        3. Player hasn't exceeded daily bet limit (1,000,000)

        Returns:
            Tuple of (can_bet: bool, reason: str)
        """
        # Check bet amount range
        if bet_amount < 1 or bet_amount > 100_000:
            return False, "下注金額必須在 1 到 100,000 之間"

        # Check player currency
        result = await self.db.exec(select(Player).where(Player.id == player_id))
        player = result.first()
        if not player or player.currency < bet_amount:
            return False, f"你沒有足夠的米幣進行下注 (需要: {bet_amount})"

        # Check daily bet limit
        can_bet = await self.check_daily_bet_limit(player_id, bet_amount)
        if not can_bet:
            week = self.get_current_week()
            rank = await self.get_player_rank(player_id, week)
            remaining = 1_000_000 - rank.daily_bet_amount
            return False, f"超過每日下注上限 (剩餘額度: {remaining})"

        return True, ""

    async def process_duel_bet(self, winner_id: int, loser_id: int, bet_amount: int) -> None:
        """Process bet transfer after a duel.

        Transfers bet amount from loser to winner and logs the transaction.
        """
        # Get both players
        result = await self.db.exec(select(Player).where(Player.id == winner_id))
        winner = result.first()
        result = await self.db.exec(select(Player).where(Player.id == loser_id))
        loser = result.first()

        if not winner or not loser:
            msg = "無法找到玩家資訊"
            raise ValueError(msg)

        if loser.currency < bet_amount:
            msg = f"玩家 {loser_id} 沒有足夠的米幣支付賭注"
            raise ValueError(msg)

        # Transfer currency
        loser.currency -= bet_amount
        winner.currency += bet_amount

        self.db.add(winner)
        self.db.add(loser)

        # Log events
        winner_event = EventLog(
            player_id=winner_id,
            event_type=EventType.EARN_MONEY,
            context={"amount": bet_amount, "reason": "決鬥獲勝", "opponent_id": loser_id},
        )
        loser_event = EventLog(
            player_id=loser_id,
            event_type=EventType.SPEND_MONEY,
            context={"amount": bet_amount, "reason": "決鬥失敗", "opponent_id": winner_id},
        )
        self.db.add(winner_event)
        self.db.add(loser_event)

        await self.db.commit()

    async def update_scores_after_battle(
        self, winner_id: int, loser_id: int, week: int | None = None
    ) -> tuple[int, int]:
        """Update scores after a ranked battle.

        Returns:
            Tuple of (score_gained_by_winner, score_lost_by_loser)
        """
        if week is None:
            week = self.get_current_week()

        winner_rank_obj = await self.get_player_rank(winner_id, week)
        loser_rank_obj = await self.get_player_rank(loser_id, week)

        winner_rank = await self.get_player_leaderboard_rank(winner_id, week)
        loser_rank = await self.get_player_leaderboard_rank(loser_id, week)

        # Calculate score transfer
        score_change = self.calculate_score_change(winner_rank, loser_rank, loser_rank_obj.points)

        # Update scores
        winner_rank_obj.points += score_change
        winner_rank_obj.score_updated_at = get_utc8_now()

        loser_rank_obj.points = max(0, loser_rank_obj.points - score_change)
        # Only update loser's timestamp if their score actually changed
        if score_change > 0:
            loser_rank_obj.score_updated_at = get_utc8_now()

        self.db.add(winner_rank_obj)
        self.db.add(loser_rank_obj)

        # Log events
        winner_event = EventLog(
            player_id=winner_id,
            event_type=EventType.RANKED_SCORE_GAINED,
            context={
                "score_gained": score_change,
                "new_score": winner_rank_obj.points,
                "opponent_id": loser_id,
            },
        )
        loser_event = EventLog(
            player_id=loser_id,
            event_type=EventType.RANKED_SCORE_LOST,
            context={
                "score_lost": score_change,
                "new_score": loser_rank_obj.points,
                "opponent_id": winner_id,
            },
        )
        self.db.add(winner_event)
        self.db.add(loser_event)

        await self.db.commit()

        return score_change, score_change

    async def reset_weekly_rankings(self) -> int:
        """Reset all rankings to 50 for the new week. Returns count of reset players."""
        old_week = self.get_current_week() - 1
        new_week = self.get_current_week()

        # Get all players from last week
        result = await self.db.exec(select(PvPRank).where(col(PvPRank.week) == old_week))
        old_ranks = result.all()

        reset_count = 0
        for old_rank in old_ranks:
            # Create new week entry
            new_rank = PvPRank(
                player_id=old_rank.player_id,
                week=new_week,
                points=50,
                score_updated_at=get_utc8_now(),
                daily_plays=0,
            )
            self.db.add(new_rank)
            reset_count += 1

        await self.db.commit()
        return reset_count

    async def distribute_weekly_rewards(self) -> int:
        """Distribute rewards to top 100 players. Returns count of rewarded players."""
        week = self.get_current_week() - 1  # Previous week
        leaderboard = await self.get_leaderboard(week, limit=100)

        reward_tiers = {
            1: 50_000,
            2: 40_000,
            3: 30_000,
            (4, 5): 20_000,
            (6, 10): 10_000,
            (11, 100): 1_000,
        }

        rewarded_count = 0
        for entry in leaderboard:
            reward = 0
            for tier, amount in reward_tiers.items():
                if isinstance(tier, int):
                    if entry.rank == tier:
                        reward = amount
                        break
                elif tier[0] <= entry.rank <= tier[1]:
                    reward = amount
                    break

            if reward > 0:
                # Get player and add currency
                result = await self.db.exec(select(Player).where(Player.id == entry.player_id))
                player = result.first()
                if player:
                    player.currency += reward
                    self.db.add(player)

                    # Log the reward
                    event_log = EventLog(
                        player_id=entry.player_id,
                        event_type=EventType.RANKED_WEEKLY_REWARD,
                        context={
                            "rank": entry.rank,
                            "reward": reward,
                            "week": week,
                            "final_score": entry.points,
                        },
                    )
                    self.db.add(event_log)
                    rewarded_count += 1

        await self.db.commit()
        return rewarded_count

    async def create_pvp_rank(self, pvp_rank: PvPRank) -> PvPRank:
        self.db.add(pvp_rank)
        await self.db.commit()
        await self.db.refresh(pvp_rank)
        return pvp_rank

    async def update_pvp_rank(self, pvp_rank_id: int, pvp_rank: PvPRankUpdate) -> PvPRank | None:
        existing_pvp_rank = await self.get_pvp_rank(pvp_rank_id)
        if not existing_pvp_rank:
            return None

        pvp_rank_data = pvp_rank.model_dump(exclude_unset=True)
        existing_pvp_rank.sqlmodel_update(pvp_rank_data)
        self.db.add(existing_pvp_rank)
        await self.db.commit()
        await self.db.refresh(existing_pvp_rank)
        return existing_pvp_rank

    async def delete_pvp_rank(self, pvp_rank_id: int) -> bool:
        pvp_rank = await self.get_pvp_rank(pvp_rank_id)
        if not pvp_rank:
            return False

        await self.db.delete(pvp_rank)
        await self.db.commit()
        return True
