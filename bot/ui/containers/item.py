import discord

from app.models.shop_item import ShopItem
from app.services.shop_item import ShopItemService
from bot import ui
from bot.types import Interaction
from bot.utils.db import get_session


class BuyItem(ui.Button):
    def __init__(self, shop_item_id: int, price: int) -> None:
        super().__init__(label=f"購買 ({price} 米幣)", style=discord.ButtonStyle.success)
        self.shop_item_id = shop_item_id
        self.price = price

    async def callback(self, i: Interaction) -> None:
        async with get_session() as session:
            service = ShopItemService(session)
            await service.purchase_shop_item(player_id=i.user.id, shop_item_id=self.shop_item_id)


class ItemContainer(ui.Container):
    def __init__(self, shop_item: ShopItem, *, buy: bool = False) -> None:
        super().__init__(ui.TextDisplay(content=f"# {shop_item.name}\n"))
        self.shop_item = shop_item

        items: list[ui.Item] = []
        if buy:
            items.append(BuyItem(shop_item_id=shop_item.id, price=shop_item.price))

        if items:
            self.add_item(ui.ActionRow(*items))
