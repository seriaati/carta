from discord import Interaction, app_commands
from fastapi import HTTPException
from loguru import logger


async def error_handler(i: Interaction, error: Exception) -> None:
    e = error.original if isinstance(error, app_commands.CommandInvokeError) else error

    if isinstance(e, HTTPException):
        message = e.detail
    else:
        logger.exception("Unexpected error occurred")
        message = "發生未知錯誤，請稍後再試。"

    if not i.response.is_done():
        await i.response.send_message(message, ephemeral=True)
    else:
        await i.followup.send(message, ephemeral=True)
