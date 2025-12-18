import discord

from app.models.trade import Trade
from app.services.deck_card import DeckCardService
from app.services.inventory import InventoryService
from app.services.player import PlayerService
from app.services.trade import TradeService
from bot import ui
from bot.utils.db import get_session


class AcceptTradeButton(ui.Button):
    def __init__(self, trade: Trade) -> None:
        self.trade = trade
        super().__init__(label="接受交易", style=discord.ButtonStyle.success)

    async def callback(self, i: discord.Interaction) -> None:
        await i.response.defer()

        async with get_session() as session:
            player_service = PlayerService(session)
            deck_card_service = DeckCardService(session)
            inventory_service = InventoryService(session, deck_card_service)
            trade_service = TradeService(
                session, player_service, inventory_service, deck_card_service
            )
            await trade_service.accept_trade(self.trade.id, i.user.id)

        if self.trade.requested_card_id is not None:
            await i.followup.send(f"{i.user.mention} 接受了這筆交易, 卡牌已交換。")
        else:
            await i.followup.send(f"{i.user.mention} 接受了這筆交易, 米幣已轉帳。")


class CardForCardTradeRequestContainer(ui.Container):
    def __init__(self, trade: Trade, image: discord.File) -> None:
        super().__init__(
            ui.TextDisplay(
                content=f"# 交易請求\n"
                f"### 發起人: <@{trade.proposer_id}>\n"
                f"### 對象: <@{trade.receiver_id}>\n"
                f"### {trade.offered_card} 換 {trade.requested_card}"
            ),
            ui.MediaGallery(discord.MediaGalleryItem(media=image)),
            ui.ActionRow(AcceptTradeButton(trade)),
        )


class CardForMoneyTradeRequestContainer(ui.Container):
    def __init__(self, trade: Trade) -> None:
        super().__init__(
            ui.TextDisplay(
                content=f"# 交易請求\n"
                f"### 發起人: <@{trade.proposer_id}>\n"
                f"### 對象: <@{trade.receiver_id}>\n"
                f"### {trade.offered_card} 換 {trade.price} 米幣"
            ),
            ui.MediaGallery(discord.MediaGalleryItem(media=trade.offered_card.image_url)),
            ui.ActionRow(AcceptTradeButton(trade)),
        )
