"""Pytest fixtures.

State-machine tests are pure and need no database. The webhook/API tests run
the FastAPI app against an in-memory SQLite database wired via FastAPI's
dependency override (the portable GUID type lets the PostgreSQL schema run on
SQLite unchanged). A StaticPool keeps the single in-memory connection alive for
the whole test.
"""
import hashlib
import hmac
import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

WEBHOOK_SECRET = "test-secret"

# Ensure the app's HMAC secret matches the one tests sign with. Set before the
# app (and its settings) are imported anywhere.
os.environ["WEBHOOK_SECRET"] = WEBHOOK_SECRET


def sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest_asyncio.fixture
async def client():
    from app.config import get_settings

    get_settings.cache_clear()

    from app.db import Base, get_session
    from app.main import app

    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSession = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_session():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()
