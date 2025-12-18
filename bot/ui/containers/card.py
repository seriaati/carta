import discord

from app.core.enums import CardRarity
from app.models.card import Card
from app.models.shop_item import ShopItem
from app.services.deck_card import DeckCardService
from app.services.inventory import InventoryService
from app.services.shop_item import ShopItemService
from bot import ui
from bot.types import Interaction
from bot.utils.db import get_session

CARD_RARITY_COLORS = {
    CardRarity.C: discord.Color.light_gray(),
    CardRarity.R: discord.Color.blue(),
    CardRarity.SR: discord.Color.purple(),
    CardRarity.SSR: discord.Color.gold(),
    CardRarity.UR: discord.Color.red(),
    CardRarity.LR: discord.Color.red(),
    CardRarity.EX: discord.Color.dark_gold(),
}


class DeckCardPositionModal(ui.Modal, title="選擇卡牌位置"):
    position: ui.Label[ui.Select] = ui.Label(
        text="卡牌位置",
        component=ui.Select(
            placeholder="選擇卡牌位置 (1-6)",
            options=[discord.SelectOption(label=str(i), value=str(i)) for i in range(1, 7)],
        ),
    )

    def __init__(self, card_id: int) -> None:
        super().__init__()
        self.card_id = card_id

    async def on_submit(self, i: Interaction) -> None:
        async with get_session() as session:
            position = int(self.position.component.values[0])
            deck_card_service = DeckCardService(session)
            await deck_card_service.add_card_to_deck(
                player_id=i.user.id, card_id=self.card_id, position=position
            )

        await i.response.send_message(f"已將卡牌加入牌組位置 {position}", ephemeral=True)


class AddCardToDeck(ui.Button):
    def __init__(self, card_id: int) -> None:
        super().__init__(label="加入牌組", style=discord.ButtonStyle.green)
        self.card_id = card_id

    async def callback(self, i: Interaction) -> None:
        modal = DeckCardPositionModal(card_id=self.card_id)
        await i.response.send_modal(modal)


class BuyCard(ui.Button):
    def __init__(self, shop_item_id: int, price: int) -> None:
        super().__init__(label=f"購買 ({price} 米幣)", style=discord.ButtonStyle.success)
        self.shop_item_id = shop_item_id
        self.price = price

    async def callback(self, i: Interaction) -> None:
        async with get_session() as session:
            service = ShopItemService(session)
            await service.purchase_shop_item(player_id=i.user.id, shop_item_id=self.shop_item_id)

        await i.response.send_message("購買成功", ephemeral=True)


class SellCard(ui.Button):
    def __init__(self, card_id: int) -> None:
        super().__init__(label="賣1張", style=discord.ButtonStyle.danger)
        self.card_id = card_id

    async def callback(self, i: Interaction) -> None:
        async with get_session() as session:
            deck_card_service = DeckCardService(session)
            service = InventoryService(session, deck_card_service=deck_card_service)
            result = await service.sell_card(player_id=i.user.id, card_id=self.card_id)

        container = ui.Container(
            ui.TextDisplay(
                content="## 賣出成功\n"
                f"獲得米幣: {result.total_value}\n"
                f"當前餘額: {result.new_currency_balance} 米幣"
            )
        )

        view = ui.LayoutView()
        view.add_item(container)

        await i.response.send_message(view=view, ephemeral=True)


class SellAllCards(ui.Button):
    def __init__(self, card_id: int, quantity: int) -> None:
        super().__init__(label=f"賣出全部 ({quantity} 張)", style=discord.ButtonStyle.danger)
        self.card_id = card_id
        self.quantity = quantity

    async def callback(self, i: Interaction) -> None:
        async with get_session() as session:
            deck_card_service = DeckCardService(session)
            service = InventoryService(session, deck_card_service)
            result = await service.sell_all_cards(player_id=i.user.id, card_id=self.card_id)

        container = ui.Container(
            ui.TextDisplay(
                content="## 賣出成功\n"
                f"獲得米幣: {result.total_value}\n"
                f"當前餘額: {result.new_currency_balance} 米幣"
            )
        )
        view = ui.LayoutView()
        view.add_item(container)
        await i.response.send_message(view=view, ephemeral=True)


class CardContainer(ui.Container):
    def __init__(  # noqa: PLR0913
        self,
        card: Card,
        *,
        shop_item: ShopItem | None = None,
        buy: bool = False,
        deck: bool = False,
        sell: bool = False,
        quantity: int | None = None,
        owner_count: int | None = None,
    ) -> None:
        # Build the content string
        content = f"### 卡牌資訊\nNo. {card.id}\n稀有度: {card.rarity}\n市價: {card.price} 米幣\n"

        # Add quantity and owner count if available
        if quantity is not None:
            content += f"持有數量: {quantity}\n"
        if owner_count is not None:
            content += f"擁有者數量: {owner_count} 位玩家\n"

        content += (
            f"### 卡牌屬性\n"
            f"攻擊力: {card.attack or '無'}\n"
            f"防禦力: {card.defense or '無'}\n"
            f"### 能力敘述\n"
            f"{card.description}\n"
        )

        super().__init__(
            ui.TextDisplay(content=f"# {card.name}"),
            ui.MediaGallery(discord.MediaGalleryItem(media=card.image_url)),
            ui.TextDisplay(content=content),
            accent_color=CARD_RARITY_COLORS.get(card.rarity, discord.Color.default()),
        )

        items: list[ui.Item] = []
        if buy:
            if shop_item is None:
                msg = "CardContainer initialized with buy=True but shop_item is None."
                raise ValueError(msg)
            items.append(BuyCard(shop_item_id=shop_item.id, price=shop_item.price))
        if deck:
            items.append(AddCardToDeck(card_id=card.id))
        if sell:
            items.append(SellCard(card_id=card.id))
            if quantity and quantity > 1:
                items.append(SellAllCards(card_id=card.id, quantity=quantity))

        if items:
            self.add_item(ui.ActionRow(*items))
