import io

import discord
from discord import app_commands
from discord.ext import commands

from app.services.deck_card import DeckCardService
from app.services.inventory import InventoryService
from bot.main import CardGameBot
from bot.types import Interaction
from bot.utils.db import get_session
from bot.utils.deck_image import generate_deck_image


class DeckCog(commands.Cog):
    def __init__(self, bot: CardGameBot) -> None:
        self.bot = bot

    @app_commands.command(name="deck_show", description="顯示你的牌組")
    async def deck_show(self, i: Interaction) -> None:
        await i.response.defer(ephemeral=True)

        async with get_session() as session:
            deck_card_service = DeckCardService(session)
            deck = await deck_card_service.get_player_deck(i.user.id)
            if not deck:
                await i.response.send_message("你的牌組目前是空的。", ephemeral=True)
                return

        image_bytes = await generate_deck_image(deck)
        buffer = io.BytesIO(image_bytes)
        buffer.seek(0)
        file_ = discord.File(fp=buffer, filename="deck.png")
        await i.edit_original_response(attachments=[file_])

    @app_commands.command(name="deck_set", description="選擇一張牌上陣")
    @app_commands.rename(card_id="卡牌", position="位置")
    @app_commands.describe(card_id="你想要放入牌組的卡牌", position="你想要放置卡牌的位置 (1-6)")
    async def deck_set(
        self, i: Interaction, card_id: int, position: app_commands.Range[int, 1, 6]
    ) -> None:
        await i.response.defer(ephemeral=True)

        async with get_session() as session:
            deck_card_service = DeckCardService(session)
            await deck_card_service.add_card_to_deck(
                player_id=i.user.id, card_id=card_id, position=position
            )

        await i.followup.send(f"已將卡牌設置到牌組位置 {position}。", ephemeral=True)

    @deck_set.autocomplete("card_id")
    async def deck_set_card_id_autocomplete(
        self, i: Interaction, current: str
    ) -> list[app_commands.Choice[int]]:
        async with get_session() as session:
            inventory_service = InventoryService(session, DeckCardService(session))
            cards = await inventory_service.get_player_cards(i.user.id)

        return [
            app_commands.Choice(name=f"{card.name} (ID: {card.id})", value=card.id)
            for card, _, _ in cards
            if current.lower() in card.name.lower() or current in str(card.id)
        ][:25]

    @app_commands.command(name="deck_unset", description="從牌組中移除一張牌")
    @app_commands.rename(position="位置")
    @app_commands.describe(position="你想要移除卡牌的位置 (1-6)")
    async def deck_unset(self, i: Interaction, position: app_commands.Range[int, 1, 6]) -> None:
        await i.response.defer(ephemeral=True)

        async with get_session() as session:
            deck_card_service = DeckCardService(session)
            success = await deck_card_service.remove_card_from_deck(
                player_id=i.user.id, position=position
            )
            if not success:
                await i.followup.send(f"位置 {position} 沒有卡牌可以移除。", ephemeral=True)
                return

        await i.followup.send(f"已從牌組位置 {position} 移除卡牌。", ephemeral=True)

    @app_commands.command(name="deck_clear", description="清空你的牌組")
    async def deck_clear(self, i: Interaction) -> None:
        await i.response.defer(ephemeral=True)

        async with get_session() as session:
            deck_card_service = DeckCardService(session)
            await deck_card_service.clear_player_deck(player_id=i.user.id)

        await i.followup.send("已清空你的牌組。", ephemeral=True)


async def setup(bot: CardGameBot) -> None:
    await bot.add_cog(DeckCog(bot))
