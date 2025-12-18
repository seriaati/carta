import asyncio

import discord

from app.core.enums import PvPMode, PvPStatus
from app.models.pvp_challenge import PvPChallenge
from app.schemas.pvp_challenge import RankingStakeCalculation
from app.services.pvp_battle import PvPBattleService
from app.services.pvp_challenge import PvPChallengeService
from app.services.pvp_rank import PvPRankService
from app.services.settings import SettingsService
from bot import ui
from bot.types import Interaction
from bot.utils.db import get_session


class PvPAccept(ui.Button):
    def __init__(
        self, *, challenger_id: int, opponent_id: int, challenger_fee: int, opponent_fee: int
    ) -> None:
        self.challenger_id = challenger_id
        self.opponent_id = opponent_id
        self.challenger_fee = challenger_fee
        self.opponent_fee = opponent_fee
        super().__init__(label="接受挑戰", style=discord.ButtonStyle.green)

    async def callback(self, i: Interaction) -> None:
        # Validate that only the opponent can accept the challenge
        if i.user.id != self.opponent_id:
            await i.response.send_message("只有被挑戰者可以接受挑戰！", ephemeral=True)
            return

        await i.response.send_message(f"<@{self.opponent_id}> 已接受挑戰, 正在收取參賽費用...")
        async with get_session() as session:
            pvp_rank_service = PvPRankService(session)
            try:
                await pvp_rank_service.charge_play_fee(self.challenger_id, self.challenger_fee)
            except Exception as e:
                await i.edit_original_response(content=f"無法收取挑戰者參賽費用: {e}")
                return

            try:
                await pvp_rank_service.charge_play_fee(self.opponent_id, self.opponent_fee)
            except Exception as e:
                await i.edit_original_response(content=f"無法收取對手參賽費用: {e}")
                return

        await i.edit_original_response(content="正在創建對戰房間...")

        async with get_session() as session:
            pvp_challenge_service = PvPChallengeService(session)
            pvp_challenge = PvPChallenge(
                challenger_id=self.challenger_id,
                opponent_id=self.opponent_id,
                status=PvPStatus.ONGOING,
                mode=PvPMode.RANKED,
            )
            try:
                await pvp_challenge_service.create_pvp_challenge(pvp_challenge)
            except Exception as e:
                await i.edit_original_response(content=f"無法創建對戰房間: {e}")
                return

        async with get_session() as session:
            pvp_rank_service = PvPRankService(session)
            try:
                await pvp_rank_service.increment_daily_plays(self.challenger_id)
            except Exception as e:
                await i.edit_original_response(content=f"無法更新挑戰者對戰次數: {e}")
                return
            try:
                await pvp_rank_service.increment_daily_plays(self.opponent_id)
            except Exception as e:
                await i.edit_original_response(content=f"無法更新對手對戰次數: {e}")
                return

        await i.edit_original_response(content="房間創建完成, 對戰即將開始!")
        await asyncio.sleep(2)
        await i.edit_original_response(content="對戰開始! AI 正在模擬對戰過程...")

        async with get_session() as session:
            settings_service = SettingsService(session)
            pvp_battle_service = PvPBattleService(session, settings_service=settings_service)
            result = await pvp_battle_service.execute_battle(
                challenger_id=self.challenger_id, opponent_id=self.opponent_id, mode=PvPMode.RANKED
            )

        await i.edit_original_response(content=result.battle_narrative)

        await i.followup.send(f"對戰結束! <@{result.winner_id}> 獲勝!")


class PvPFriendlyAccept(ui.Button):
    def __init__(self, *, challenger_id: int, opponent_id: int) -> None:
        self.challenger_id = challenger_id
        self.opponent_id = opponent_id
        super().__init__(label="接受挑戰", style=discord.ButtonStyle.green)

    async def callback(self, i: Interaction) -> None:
        # Validate that only the opponent can accept the challenge
        if i.user.id != self.opponent_id:
            await i.response.send_message("只有被挑戰者可以接受挑戰！", ephemeral=True)
            return

        await i.response.send_message(f"<@{self.opponent_id}> 已接受挑戰, 正在創建對戰房間...")

        async with get_session() as session:
            pvp_challenge_service = PvPChallengeService(session)
            pvp_challenge = PvPChallenge(
                challenger_id=self.challenger_id,
                opponent_id=self.opponent_id,
                status=PvPStatus.ONGOING,
                mode=PvPMode.FRIENDLY,
            )
            try:
                await pvp_challenge_service.create_pvp_challenge(pvp_challenge)
            except Exception as e:
                await i.edit_original_response(content=f"無法創建對戰房間: {e}")
                return

        await i.edit_original_response(content="房間創建完成, 對戰即將開始!")
        await asyncio.sleep(2)
        await i.edit_original_response(content="對戰開始! AI 正在模擬對戰過程...")

        async with get_session() as session:
            settings_service = SettingsService(session)
            pvp_battle_service = PvPBattleService(session, settings_service=settings_service)
            result = await pvp_battle_service.execute_battle(
                challenger_id=self.challenger_id,
                opponent_id=self.opponent_id,
                mode=PvPMode.FRIENDLY,
            )

        await i.edit_original_response(content=result.battle_narrative)

        await i.followup.send(f"對戰結束! <@{result.winner_id}> 獲勝!")


class PvPDuelAccept(ui.Button):
    def __init__(self, *, challenger_id: int, opponent_id: int, bet_amount: int) -> None:
        self.challenger_id = challenger_id
        self.opponent_id = opponent_id
        self.bet_amount = bet_amount
        super().__init__(label="接受挑戰", style=discord.ButtonStyle.green)

    async def callback(self, i: Interaction) -> None:
        # Validate that only the opponent can accept the challenge
        if i.user.id != self.opponent_id:
            await i.response.send_message("只有被挑戰者可以接受挑戰！", ephemeral=True)
            return

        await i.response.send_message(f"<@{self.opponent_id}> 已接受挑戰, 正在驗證雙方資金...")

        # Validate both players can bet
        async with get_session() as session:
            pvp_rank_service = PvPRankService(session)

            # Check challenger
            can_bet, reason = await pvp_rank_service.validate_player_can_bet(
                self.challenger_id, self.bet_amount
            )
            if not can_bet:
                await i.edit_original_response(content=f"挑戰者無法下注: {reason}")
                return

            # Check opponent
            can_bet, reason = await pvp_rank_service.validate_player_can_bet(
                self.opponent_id, self.bet_amount
            )
            if not can_bet:
                await i.edit_original_response(content=f"對手無法下注: {reason}")
                return

            # Increment daily bet amounts for both players
            try:
                await pvp_rank_service.increment_daily_bet_amount(
                    self.challenger_id, self.bet_amount
                )
                await pvp_rank_service.increment_daily_bet_amount(self.opponent_id, self.bet_amount)
            except Exception as e:
                await i.edit_original_response(content=f"無法記錄下注金額: {e}")
                return

        await i.edit_original_response(content="資金驗證通過，正在創建對戰房間...")

        async with get_session() as session:
            pvp_challenge_service = PvPChallengeService(session)
            pvp_challenge = PvPChallenge(
                challenger_id=self.challenger_id,
                opponent_id=self.opponent_id,
                status=PvPStatus.ONGOING,
                mode=PvPMode.DUEL,
                bet=self.bet_amount,
            )
            try:
                await pvp_challenge_service.create_pvp_challenge(pvp_challenge)
            except Exception as e:
                await i.edit_original_response(content=f"無法創建對戰房間: {e}")
                return

        await i.edit_original_response(content="房間創建完成, 對戰即將開始!")
        await asyncio.sleep(2)
        await i.edit_original_response(content="對戰開始! AI 正在模擬對戰過程...")

        async with get_session() as session:
            settings_service = SettingsService(session)
            pvp_battle_service = PvPBattleService(session, settings_service=settings_service)
            result = await pvp_battle_service.execute_battle(
                challenger_id=self.challenger_id,
                opponent_id=self.opponent_id,
                mode=PvPMode.DUEL,
                bet_amount=self.bet_amount,
            )

        await i.edit_original_response(content=result.battle_narrative)

        loser_id = (
            self.opponent_id if result.winner_id == self.challenger_id else self.challenger_id
        )
        await i.followup.send(
            f"對戰結束! <@{result.winner_id}> 獲勝並贏得 {self.bet_amount} 米幣!\n"
            f"<@{loser_id}> 損失 {self.bet_amount} 米幣。"
        )


class PvPRankedRequestContainer(ui.Container):
    def __init__(
        self,
        opponent: discord.User | discord.Member,
        *,
        stakes: RankingStakeCalculation,
        challenger_fee: int,
        opponent_fee: int,
    ) -> None:
        self.opponent = opponent
        super().__init__(
            ui.TextDisplay(
                f"# 排位賽對戰請求\n"
                "## 對戰資訊\n"
                f"發起者: <@{stakes.challenger_id}> (#{stakes.challenger_rank} - {stakes.challenger_score}分)\n"
                f"對手: <@{stakes.opponent_id}> (#{stakes.opponent_rank} - {stakes.opponent_score}分)\n"
                "## 分數資訊\n"
                f"<@{stakes.challenger_id}> 勝利可獲得: {stakes.challenger_wins_stake} 分\n"
                f"<@{stakes.opponent_id}> 勝利可獲得: {stakes.opponent_wins_stake} 分\n"
                "## 參賽費用\n"
                f"<@{stakes.challenger_id}> 需支付參賽費用: {challenger_fee} 米幣\n"
                f"<@{stakes.opponent_id}> 需支付參賽費用: {opponent_fee} 米幣\n"
            ),
            ui.ActionRow(
                PvPAccept(
                    challenger_id=stakes.challenger_id,
                    opponent_id=stakes.opponent_id,
                    challenger_fee=challenger_fee,
                    opponent_fee=opponent_fee,
                )
            ),
        )


class PvPFriendlyRequestContainer(ui.Container):
    def __init__(self, opponent: discord.User | discord.Member, *, challenger_id: int) -> None:
        self.opponent = opponent
        super().__init__(
            ui.TextDisplay(
                f"# 友誼賽對戰請求\n"
                "## 對戰資訊\n"
                f"發起者: <@{challenger_id}>\n"
                f"對手: <@{opponent.id}>\n\n"
                "這是一場友誼賽，不會收取任何費用，也不會影響排位分數！\n"
            ),
            ui.ActionRow(PvPFriendlyAccept(challenger_id=challenger_id, opponent_id=opponent.id)),
        )


class PvPDuelRequestContainer(ui.Container):
    def __init__(
        self, opponent: discord.User | discord.Member, *, challenger_id: int, bet_amount: int
    ) -> None:
        self.opponent = opponent
        super().__init__(
            ui.TextDisplay(
                f"# 決鬥對戰請求\n"
                "## 對戰資訊\n"
                f"發起者: <@{challenger_id}>\n"
                f"對手: <@{opponent.id}>\n"
                f"賭注: {bet_amount:,} 米幣\n\n"
                "**勝利者將贏得對方的賭注！**\n"
                "此對戰不會影響排位分數。\n"
            ),
            ui.ActionRow(
                PvPDuelAccept(
                    challenger_id=challenger_id, opponent_id=opponent.id, bet_amount=bet_amount
                )
            ),
        )
