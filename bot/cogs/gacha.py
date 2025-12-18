from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from app.services.card_pool import CardPoolService
from app.services.gacha import GachaService
from bot.main import CardGameBot
from bot.types import Interaction
from bot.utils.db import get_session


class GachaCog(commands.Cog):
    def __init__(self, bot: CardGameBot) -> None:
        self.bot = bot

    @app_commands.command(name="draw", description="進行抽卡")
    @app_commands.rename(card_pool_id="卡池", count="抽卡類型")
    @app_commands.choices(
        count=[
            app_commands.Choice(name="單抽", value=1),
            app_commands.Choice(name="十連抽", value=10),
        ]
    )
    async def draw(self, i: Interaction, card_pool_id: str, count: Literal[1, 10]) -> None:
        async with get_session() as session:
            service = CardPoolService(session)
            card_pool = await service.get_card_pool(int(card_pool_id))
            if not card_pool:
                await i.response.send_message("找不到指定的卡池。", ephemeral=True)
                return

        async with get_session() as session:
            gacha = GachaService(session)
            results, remaining_currency = await gacha.pull_cards(i.user.id, card_pool.id, count)

            embed = discord.Embed(
                title=f"抽卡結果 - {card_pool.name}",
                description=f"剩餘米幣: {remaining_currency}",
                color=discord.Color.blue(),
            )
            for idx, result in enumerate(results, start=1):
                pity_text = " (保底)" if result.was_pity else ""
                embed.add_field(
                    name=f"抽卡 {idx}{pity_text}",
                    value=f"{result.card_name} (稀有度: {result.card_rarity.name})",
                    inline=False,
                )

            await i.response.send_message(embed=embed)

    @app_commands.command(name="draw_pity", description="查看卡池的當前保底進度")
    @app_commands.rename(card_pool_id="卡池")
    async def draw_pity(self, i: Interaction, card_pool_id: str) -> None:
        async with get_session() as session:
            service = CardPoolService(session)
            card_pool = await service.get_card_pool(int(card_pool_id))
            if not card_pool:
                await i.response.send_message("找不到指定的卡池。", ephemeral=True)
                return

            gacha = GachaService(session)
            pity = await gacha.get_pity_count(i.user.id, card_pool.id)

            embed = discord.Embed(
                title=f"{card_pool.name} - 保底進度",
                description=f"當前保底次數: {pity.current_pity} / 1000",
                color=discord.Color.green(),
            )

            await i.response.send_message(embed=embed)

    @draw.autocomplete("card_pool_id")
    @draw_pity.autocomplete("card_pool_id")
    async def card_pool_autocomplete(
        self, _i: Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        async with get_session() as session:
            service = CardPoolService(session)
            card_pools = await service.get_all_card_pools()
            choices = [
                app_commands.Choice(name=pool.name, value=str(pool.id)) for pool in card_pools
            ]
            return [choice for choice in choices if current.lower() in choice.name.lower()][:25]


async def setup(bot: CardGameBot) -> None:
    await bot.add_cog(GachaCog(bot))
