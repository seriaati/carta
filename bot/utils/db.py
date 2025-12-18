from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import engine


def get_session() -> AsyncSession:
    return AsyncSession(engine)
