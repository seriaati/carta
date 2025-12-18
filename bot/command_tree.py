import contextlib

import discord
from discord import app_commands
from sqlalchemy.exc import IntegrityError

from app.models.player import Player
from app.services.player import PlayerService
from bot.utils.db import get_session
from bot.utils.error_handler import error_handler


class CommandTree(app_commands.CommandTree):
    async def on_error(self, i: discord.Interaction, error: app_commands.AppCommandError) -> None:
        return await error_handler(i, error)

    async def interaction_check(self, i: discord.Interaction) -> bool:
        async with get_session() as session:
            player_service = PlayerService(session)
            with contextlib.suppress(IntegrityError):
                await player_service.create_player(
                    Player(id=i.user.id, name=i.user.global_name or i.user.name)
                )
        return True
