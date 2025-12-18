from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings

engine = create_async_engine(settings.db_url)


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with AsyncSession(
        engine, autocommit=False, autoflush=False, expire_on_commit=False
    ) as session:
        yield session
