"""Pytest fixtures.

State-machine tests are pure and need no database. The webhook/API tests run
the FastAPI app against an in-memory SQLite database wired via FastAPI's
dependency override (integer autoincrement keys run on SQLite unchanged, so no
special column type is needed). A StaticPool keeps the single in-memory
connection alive for the whole test.
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

# La configuración (app/config.py) ya no tiene valores por defecto: TODAS las
# variables son obligatorias y deben venir del entorno. En tests las fijamos
# aquí, ANTES de importar la app (y por tanto sus settings). Esto además hace
# los tests independientes de cualquier api/.env (que no se versiona y no existe
# en CI). Las variables de entorno tienen prioridad sobre el archivo .env.
os.environ["WEBHOOK_SECRET"] = WEBHOOK_SECRET
os.environ["JWT_SECRET"] = "test-jwt-secret"
# Base de datos / Redis: los tests usan SQLite en memoria vía dependency
# override, pero Settings igual exige estos valores al importarse.
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
# Resto de obligatorias (no sensibles) con valores de test.
os.environ["WEBHOOK_MAX_AGE_SECONDS"] = "300"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
os.environ["ADMIN_EMAIL"] = "admin@test.com"
os.environ["ADMIN_PASSWORD"] = "secret123"
# Do not run the startup seed during tests.
os.environ["DESKLY_SEED"] = "false"


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
        # Expose the session factory so fixtures/tests can prepare data.
        ac.test_session = TestSession  # type: ignore[attr-defined]
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


async def _create_user(TestSession, email: str, password: str, is_admin: bool):
    from app.models import User
    from app.security import hash_password

    async with TestSession() as session:
        user = User(
            email=email,
            hashed_password=hash_password(password),
            is_admin=is_admin,
            # nombre y apellidos son NOT NULL en el modelo User; los tests no los
            # usan pero deben proveerse para satisfacer la restricción.
            nombre="Test",
            apellidos="User",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user.id


@pytest_asyncio.fixture
async def admin_client(client):
    """A client authenticated as an admin user (Authorization header set)."""
    await _create_user(
        client.test_session, "admin@test.com", "secret123", is_admin=True
    )
    resp = await client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "secret123"},
    )
    token = resp.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
