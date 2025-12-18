from collections.abc import Sequence

from discord import ButtonStyle

from bot import ui
from bot.types import Interaction

__all__ = ("PaginatorView",)


class FirstPageButton(ui.Button["PaginatorView"]):
    def __init__(self, *, disabled: bool) -> None:
        super().__init__(style=ButtonStyle.primary, emoji="⏮️", disabled=disabled)

    async def callback(self, i: Interaction) -> None:
        assert self.view is not None
        self.view.current_page = 0
        await self.view.update_container(i)


class NextPageButton(ui.Button["PaginatorView"]):
    def __init__(self, *, disabled: bool) -> None:
        super().__init__(style=ButtonStyle.primary, emoji="▶️", disabled=disabled)

    async def callback(self, i: Interaction) -> None:
        assert self.view is not None
        if self.view.current_page < len(self.view.containers) - 1:
            self.view.current_page += 1
        await self.view.update_container(i)


class PreviousPageButton(ui.Button["PaginatorView"]):
    def __init__(self, *, disabled: bool) -> None:
        super().__init__(style=ButtonStyle.primary, emoji="◀️", disabled=disabled)

    async def callback(self, i: Interaction) -> None:
        assert self.view is not None
        if self.view.current_page > 0:
            self.view.current_page -= 1
        await self.view.update_container(i)


class LastPageButton(ui.Button["PaginatorView"]):
    def __init__(self, *, disabled: bool) -> None:
        super().__init__(style=ButtonStyle.primary, emoji="⏭️", disabled=disabled)

    async def callback(self, i: Interaction) -> None:
        assert self.view is not None
        self.view.current_page = len(self.view.containers) - 1
        await self.view.update_container(i)


class PageInfoButton(ui.Button["PaginatorView"]):
    def __init__(self, *, page: int, total_pages: int) -> None:
        super().__init__(
            style=ButtonStyle.secondary, label=f"{page + 1} / {total_pages}", disabled=True
        )

    async def callback(self, i: Interaction) -> None:
        await i.response.defer()


class PaginationControls(ui.ActionRow):
    def __init__(self, view: "PaginatorView") -> None:
        super().__init__(
            FirstPageButton(disabled=view.current_page == 0),
            PreviousPageButton(disabled=view.current_page == 0),
            PageInfoButton(page=view.current_page, total_pages=len(view.containers)),
            NextPageButton(disabled=view.current_page == len(view.containers) - 1),
            LastPageButton(disabled=view.current_page == len(view.containers) - 1),
        )


class PaginatorView(ui.LayoutView):
    def __init__(self, containers: Sequence[ui.Container]) -> None:
        super().__init__(timeout=300.0)

        self.containers = containers
        self.current_page = 0

        container = containers[self.current_page]
        action_row = PaginationControls(self)
        self.add_item(container)
        self.add_item(action_row)

    async def update_container(self, i: Interaction) -> None:
        container = self.containers[self.current_page]
        action_row = PaginationControls(self)
        self.clear_items()
        self.add_item(container)
        self.add_item(action_row)
        await i.response.edit_message(view=self)

    async def start(self, i: Interaction) -> None:
        if i.response.is_done():
            await i.edit_original_response(view=self)
        else:
            await i.response.send_message(view=self)
