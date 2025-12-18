import discord
from discord import app_commands
from discord.ext import commands

from app.services.pvp_rank import PvPRankService
from bot import ui
from bot.main import CardGameBot
from bot.types import Interaction
from bot.ui.containers.pvp import (
    PvPDuelRequestContainer,
    PvPFriendlyRequestContainer,
    PvPRankedRequestContainer,
)
from bot.ui.paginator import PaginatorView
from bot.utils.db import get_session


class PvPCog(commands.GroupCog, name="pvp", description="玩家對戰相關指令"):
    def __init__(self, bot: CardGameBot) -> None:
        self.bot = bot

    fight = app_commands.Group(name="fight", description="玩家對戰指令")

    @fight.command(name="rank", description="開始一場排位對戰")
    @app_commands.rename(player="對手")
    @app_commands.describe(player="選擇你要對戰的玩家")
    async def rank_fight(self, i: Interaction, player: discord.User | discord.Member) -> None:
        """Start a ranked PvP battle."""
        # Prevent players from challenging themselves
        if i.user.id == player.id:
            await i.response.send_message("你不能挑戰自己！", ephemeral=True)
            return

        async with get_session() as session:
            pvp_rank_service = PvPRankService(session)
            stakes = await pvp_rank_service.calculate_ranking_stakes(
                challenger_id=i.user.id, opponent_id=player.id
            )

            challenger_fee = await pvp_rank_service.check_daily_limit_and_get_fee(
                stakes.challenger_id
            )
            opponent_fee = await pvp_rank_service.check_daily_limit_and_get_fee(stakes.opponent_id)

        view = ui.LayoutView()
        view.add_item(
            PvPRankedRequestContainer(
                opponent=player,
                stakes=stakes,
                challenger_fee=challenger_fee,
                opponent_fee=opponent_fee,
            )
        )
        await i.response.send_message(view=view)
        message = await i.original_response()
        await message.reply(f"<@{player.id}> 你有一個新的排位對戰請求來自 <@{i.user.id}>!")

    @fight.command(name="friendly", description="開始一場友誼賽")
    @app_commands.rename(player="對手")
    @app_commands.describe(player="選擇你要對戰的玩家")
    async def friendly_fight(self, i: Interaction, player: discord.User | discord.Member) -> None:
        """Start a friendly PvP battle (no fees, limits, or rank changes)."""
        # Prevent players from challenging themselves
        if i.user.id == player.id:
            await i.response.send_message("你不能挑戰自己！", ephemeral=True)
            return

        view = ui.LayoutView()
        view.add_item(PvPFriendlyRequestContainer(opponent=player, challenger_id=i.user.id))
        await i.response.send_message(view=view)
        message = await i.original_response()
        await message.reply(f"<@{player.id}> 你有一個新的友誼賽請求來自 <@{i.user.id}>!")

    @fight.command(name="duel", description="開始一場決鬥 (需下注)")
    @app_commands.rename(player="對手", bet="賭注")
    @app_commands.describe(player="選擇你要對戰的玩家", bet="下注金額 (1-100,000)")
    async def duel_fight(
        self, i: Interaction, player: discord.User | discord.Member, bet: int
    ) -> None:
        """Start a duel PvP battle with a bet (no fees or rank changes)."""
        # Prevent players from challenging themselves
        if i.user.id == player.id:
            await i.response.send_message("你不能挑戰自己！", ephemeral=True)
            return

        # Validate bet amount
        if bet < 1 or bet > 100_000:
            await i.response.send_message("賭注金額必須在 1 到 100,000 之間！", ephemeral=True)
            return

        # Validate challenger can bet
        async with get_session() as session:
            pvp_rank_service = PvPRankService(session)
            can_bet, reason = await pvp_rank_service.validate_player_can_bet(i.user.id, bet)
            if not can_bet:
                await i.response.send_message(f"無法發起決鬥: {reason}", ephemeral=True)
                return

        view = ui.LayoutView()
        view.add_item(
            PvPDuelRequestContainer(opponent=player, challenger_id=i.user.id, bet_amount=bet)
        )
        await i.response.send_message(view=view)
        message = await i.original_response()
        await message.reply(f"<@{player.id}> 你有一個新的決鬥請求來自 <@{i.user.id}>!")

    @app_commands.command(name="rank", description="查看你的排位資訊")
    @app_commands.rename(near="顯示附近排名")
    @app_commands.describe(near="是否顯示你附近的排名資訊")
    @app_commands.choices(
        near=[app_commands.Choice(name="是", value=1), app_commands.Choice(name="否", value=0)]
    )
    async def view_rank(self, i: Interaction, near: int = 0) -> None:
        await i.response.defer()

        async with get_session() as session:
            pvp_rank_service = PvPRankService(session)
            if near:
                entries = await pvp_rank_service.get_leaderboard_near_player(i.user.id)
            else:
                entries = await pvp_rank_service.get_top_100_leaderboard()

            if not entries:
                await i.response.send_message("目前沒有排位資訊可供顯示。", ephemeral=True)
                return

        # Split entries by 10 per page
        containers = []
        for start in range(0, len(entries), 10):
            page_entries = entries[start : start + 10]
            container = ui.Container(
                ui.TextDisplay(
                    "# PVP 排位榜\n\n"
                    + "\n".join(
                        f"{entry.rank}. <@{entry.player_id}> - {entry.points} 分"
                        for entry in page_entries
                    )
                )
            )
            containers.append(container)

        paginator = PaginatorView(containers)
        await paginator.start(i)


async def setup(bot: CardGameBot) -> None:
    await bot.add_cog(PvPCog(bot))
