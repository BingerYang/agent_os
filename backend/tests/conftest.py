import asyncio
import os

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


def _reset_database_engine() -> None:
    from src.core import database
    from src.core.config import get_settings

    old_engine = database.engine

    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    get_settings.cache_clear()
    settings = get_settings()

    database.engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.debug,
    )
    database.AsyncSessionLocal = async_sessionmaker(
        database.engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    asyncio.run(old_engine.dispose())


def pytest_sessionstart(session: pytest.Session) -> None:
    _reset_database_engine()


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    from src.core import database

    asyncio.run(database.engine.dispose())


@pytest.fixture(scope="function", autouse=True)
async def setup_db():
    from src.core.database import Base, engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
