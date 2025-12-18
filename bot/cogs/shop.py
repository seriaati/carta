from discord import app_commands
from discord.ext import commands
from loguru import logger

from app.core.enums import ShopItemType
from app.services.shop_item import ShopItemService
from bot.main import CardGameBot
from bot.types import Interaction
from bot.ui.containers.card import CardContainer
from bot.ui.containers.item import ItemContainer
from bot.ui.paginator import PaginatorView
from bot.utils.db import get_session


class ShopCog(commands.Cog):
    def __init__(self, bot: CardGameBot) -> None:
        self.bot = bot

    @app_commands.command(name="shop", description="瀏覽卡牌商店")
    async def shop(self, i: Interaction) -> None:
        async with get_session() as session:
            service = ShopItemService(session)
            shop_items = await service.get_dynamic_shop_items(player_id=i.user.id)
            if not shop_items:
                await i.response.send_message("商店目前沒有任何商品。", ephemeral=True)
                return

            containers: list[ItemContainer | CardContainer] = []

            for item in shop_items:
                if item.type is ShopItemType.ITEM:
                    container = ItemContainer(item, buy=True)
                elif item.type is ShopItemType.CARD:
                    assert item.card is not None
                    container = CardContainer(item.card, shop_item=item, buy=True)
                else:
                    logger.warning(f"Unknown shop item type: {item.type} for item ID {item.id}")
                    continue

                containers.append(container)

            paginator = PaginatorView(containers)
            await paginator.start(i)


async def setup(bot: CardGameBot) -> None:
    await bot.add_cog(ShopCog(bot))
