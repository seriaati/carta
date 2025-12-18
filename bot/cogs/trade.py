import io

import discord
from discord import app_commands
from discord.ext import commands

from app.schemas.trade import TradeCreate
from app.services.card import CardService
from app.services.deck_card import DeckCardService
from app.services.inventory import InventoryService
from app.services.player import PlayerService
from app.services.trade import TradeService
from bot import ui
from bot.main import CardGameBot
from bot.types import Interaction
from bot.ui.containers.trade import (
    CardForCardTradeRequestContainer,
    CardForMoneyTradeRequestContainer,
)
from bot.utils.db import get_session
from bot.utils.deck_image import generate_trade_image


class TradeCog(commands.GroupCog, name="trade", description="交易相關指令"):
    def __init__(self, bot: CardGameBot) -> None:
        self.bot = bot

    @app_commands.command(name="card", description="發起交易")
    @app_commands.rename(user="對象", offered_card_id="你有的卡牌", requested_card_id="想要的卡牌")
    @app_commands.describe(
        user="選擇你要交易的玩家", offered_card_id="你有的卡牌", requested_card_id="想要的卡牌"
    )
    async def trade_card_for_card(
        self,
        i: Interaction,
        user: discord.User | discord.Member,
        offered_card_id: int,
        requested_card_id: int,
    ) -> None:
        await i.response.defer()

        async with get_session() as session:
            player_service = PlayerService(session)
            deck_card_service = DeckCardService(session)
            inventory_service = InventoryService(session, deck_card_service)
            trade_service = TradeService(
                session, player_service, inventory_service, deck_card_service
            )
            trade = TradeCreate(
                receiver_id=user.id,
                offered_card_id=offered_card_id,
                requested_card_id=requested_card_id,
            )
            trade = await trade_service.create_trade_request(i.user.id, trade)

        assert trade.requested_card is not None
        image_bytes = await generate_trade_image(trade.offered_card, trade.requested_card)
        buffer = io.BytesIO(image_bytes)
        buffer.seek(0)
        image = discord.File(fp=buffer, filename="trade_request.png")
        container = CardForCardTradeRequestContainer(trade, image)
        view = ui.LayoutView()
        view.add_item(container)

        await i.followup.send(view=view, file=image)

    @app_commands.command(name="money", description="發起交易")
    @app_commands.rename(user="對象", offered_card_id="你有的卡牌", price="米幣數量")
    @app_commands.describe(
        user="選擇你要交易的玩家", offered_card_id="你有的卡牌", price="米幣數量"
    )
    async def trade_card_for_money(
        self, i: Interaction, user: discord.User | discord.Member, offered_card_id: int, price: int
    ) -> None:
        await i.response.defer()

        async with get_session() as session:
            player_service = PlayerService(session)
            deck_card_service = DeckCardService(session)
            inventory_service = InventoryService(session, deck_card_service)
            trade_service = TradeService(
                session, player_service, inventory_service, deck_card_service
            )
            trade = TradeCreate(receiver_id=user.id, offered_card_id=offered_card_id, price=price)
            trade = await trade_service.create_trade_request(i.user.id, trade)

        container = CardForMoneyTradeRequestContainer(trade)
        view = ui.LayoutView()
        view.add_item(container)

        await i.followup.send(view=view)

    @trade_card_for_card.autocomplete("offered_card_id")
    @trade_card_for_money.autocomplete("offered_card_id")
    async def trade_card_for_card_autocomplete(
        self, i: Interaction, current: str
    ) -> list[app_commands.Choice[int]]:
        async with get_session() as session:
            inventory_service = InventoryService(session, DeckCardService(session))
            cards = await inventory_service.get_player_cards(i.user.id)

        return [
            app_commands.Choice(name=f"{card.name} (擁有數量: {quantity})", value=card.id)
            for card, quantity, _ in cards
            if current.lower() in card.name.lower()
        ][:25]

    @trade_card_for_card.autocomplete("requested_card_id")
    async def trade_card_for_card_requested_autocomplete(
        self, _i: Interaction, current: str
    ) -> list[app_commands.Choice[int]]:
        async with get_session() as session:
            card_service = CardService(session)
            cards = await card_service.get_cards_by_name(current)

        return [app_commands.Choice(name=card.name, value=card.id) for card in cards][:25]


async def setup(bot: CardGameBot) -> None:
    await bot.add_cog(TradeCog(bot))
