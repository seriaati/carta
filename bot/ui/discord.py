import discord
from discord import ui

from bot.types import Interaction
from bot.utils.error_handler import error_handler

__all__ = (
    "ActionRow",
    "Button",
    "Container",
    "Item",
    "Label",
    "LayoutView",
    "MediaGallery",
    "Modal",
    "Select",
    "TextDisplay",
)

type Item = Button | Select | Container | Label | TextDisplay | MediaGallery


class Modal(ui.Modal):
    async def on_error(self, i: Interaction, error: Exception) -> None:
        await error_handler(i, error)


class Button[V: LayoutView](ui.Button):
    view: V


class Select[V: LayoutView](ui.Select):
    view: V


class Container[V: LayoutView](ui.Container):
    view: V


class Label[I: ui.Item](ui.Label):
    component: I


class TextDisplay(ui.TextDisplay):
    pass


class MediaGallery(ui.MediaGallery):
    pass


class ActionRow(ui.ActionRow):
    @property
    def disabled(self) -> bool:
        return all(
            item.disabled for item in self.children if isinstance(item, ui.Button | ui.Select)
        )

    @disabled.setter
    def disabled(self, value: bool) -> None:
        for item in self.children:
            if isinstance(item, ui.Button | ui.Select):
                item.disabled = value


class LayoutView(ui.LayoutView):
    message: discord.Message | None = None

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, ActionRow):
                item.disabled = True

        if self.message is not None:
            await self.message.edit(view=self)

    async def on_error(self, i: Interaction, error: Exception, _item: ui.Item) -> None:
        return await error_handler(i, error)
