import anyio
import discord
from discord.ext import commands
from loguru import logger

from bot.command_tree import CommandTree


class CardGameBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=discord.Intents.default(),
            help_command=None,
            tree_cls=CommandTree,
        )

    async def _load_cogs(self) -> None:
        async for file in anyio.Path("bot/cogs").iterdir():
            if file.suffix == ".py":
                cog_name = f"bot.cogs.{file.stem}"
                await self.load_extension(cog_name)
                logger.info(f"Loaded cog: {cog_name}")

        await self.load_extension("jishaku")

    async def setup_hook(self) -> None:
        await self._load_cogs()
