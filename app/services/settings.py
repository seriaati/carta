from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.db import get_db
from app.core.enums import CardRarity
from app.models.settings import Settings


class SettingsService:
    def __init__(self, db: Annotated[AsyncSession, Depends(get_db)]) -> None:
        self.db = db

    async def _get_setting(self, key: str) -> Settings | None:
        statement = select(Settings).where(Settings.key == key)
        result = await self.db.execute(statement)
        return result.scalar_one_or_none()

    async def get_prompt(self) -> str | None:
        prompt_setting = await self._get_setting("prompt")
        return prompt_setting.value if prompt_setting else None

    async def set_prompt(self, prompt: str) -> str:
        prompt_setting = await self._get_setting("prompt")
        if prompt_setting:
            prompt_setting.value = prompt
            self.db.add(prompt_setting)
        else:
            prompt_setting = Settings(key="prompt", value=prompt)
            self.db.add(prompt_setting)

        await self.db.commit()
        return prompt_setting.value

    async def get_shop_rarity_rates(self) -> dict[CardRarity, float]:
        result: dict[CardRarity, float] = {}

        for rarity in CardRarity:
            key = f"shop_rarity_{rarity.value}"
            setting = await self._get_setting(key)
            rate = float(setting.value) if setting else 1.0
            result[rarity] = rate

        return result

    async def set_shop_rarity_rate(self, rarity: CardRarity, rate: float) -> float:
        key = f"shop_rarity_{rarity.value}"
        setting = await self._get_setting(key)
        if setting:
            setting.value = str(rate)
            self.db.add(setting)
        else:
            setting = Settings(key=key, value=str(rate))
            self.db.add(setting)

        await self.db.commit()
        return float(setting.value)
