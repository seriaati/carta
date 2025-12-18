from discord import app_commands
from discord.ext import commands

from app.core.enums import CardRarity
from app.services.card import CardService
from app.services.card_pool import CardPoolService
from app.services.deck_card import DeckCardService
from app.services.inventory import InventoryService
from app.services.player import PlayerService
from bot import ui
from bot.main import CardGameBot
from bot.types import Interaction
from bot.ui.containers.card import CardContainer
from bot.ui.paginator import PaginatorView
from bot.utils.db import get_session


class CardCog(commands.Cog):
    def __init__(self, bot: CardGameBot) -> None:
        self.bot = bot

    @app_commands.command(name="my_cards", description="列出你擁有的所有卡牌")
    @app_commands.rename(rarity="稀有度", card_id="卡牌id")
    async def my_cards(
        self, i: Interaction, rarity: CardRarity | None = None, card_id: int | None = None
    ) -> None:
        async with get_session() as session:
            deck_card_service = DeckCardService(session)
            service = InventoryService(session, deck_card_service)
            cards = await service.get_player_cards(i.user.id, rarity=rarity, card_id=card_id)
            if not cards:
                await i.response.send_message(
                    "你目前沒有擁有任何卡牌或是沒有符合條件的卡牌。", ephemeral=True
                )
                return

            containers = [
                CardContainer(
                    card, deck=True, sell=True, quantity=quantity, owner_count=owner_count
                )
                for card, quantity, owner_count in cards
            ]
            paginator = PaginatorView(containers)
            await paginator.start(i)

    @app_commands.command(name="card_search", description="搜尋卡牌資料庫中的卡牌")
    @app_commands.rename(card_id="卡牌id")
    async def card_search(self, i: Interaction, card_id: int) -> None:
        async with get_session() as session:
            service = CardService(session)
            card = await service.get_card(card_id)
            if not card:
                await i.response.send_message("找不到指定的卡牌。", ephemeral=True)
                return

            container = CardContainer(card)
            view = ui.LayoutView()
            view.add_item(container)

            await i.response.send_message(view=view)

    @app_commands.command(name="card_stats", description="顯示卡牌的統計資料")
    async def card_stats(self, i: Interaction) -> None:
        async with get_session() as session:
            service = PlayerService(session)
            statistics = await service.get_card_statistics(i.user.id)

            stats_message = f"你的卡牌統計資料:\n總卡牌數量: {statistics.total_owned_cards}\n"
            for rarity, count in statistics.cards_per_rarity.items():
                stats_message += f"稀有度 {rarity}: {count} 張卡牌\n"

            await i.response.send_message(stats_message, ephemeral=True)

    @app_commands.command(name="card_list", description="查看一個卡池的一個稀有度的所有卡牌")
    @app_commands.rename(pool_id="卡池", rarity="稀有度")
    @app_commands.describe(pool_id="你想要查看的卡池", rarity="你想要查看的卡牌稀有度")
    async def card_list(self, i: Interaction, pool_id: int, rarity: CardRarity) -> None:
        async with get_session() as session:
            service = CardPoolService(session)
            cards = await service.get_card_pool_cards_by_rarity(pool_id, rarity)
            if not cards:
                await i.response.send_message(
                    "在指定的卡池中找不到符合該稀有度的卡牌。", ephemeral=True
                )
                return

            containers = [CardContainer(card) for _id, card, _probability in cards]
            paginator = PaginatorView(containers)
            await paginator.start(i)


async def setup(bot: CardGameBot) -> None:
    await bot.add_cog(CardCog(bot))
