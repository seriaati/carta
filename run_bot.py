import asyncio
import contextlib

from app.core.config import settings
from app.utils.logging import setup_logging
from bot.main import CardGameBot


async def main() -> None:
    setup_logging("bot.log")
    bot = CardGameBot()
    with contextlib.suppress(KeyboardInterrupt, asyncio.CancelledError):
        await bot.start(settings.discord_bot_token)


if __name__ == "__main__":
    asyncio.run(main())
