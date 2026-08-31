"""Pytest fixtures.

State-machine tests are pure and need no database. The webhook/API tests run
the FastAPI app against a temporary file-based SQLite database (the portable
GUID type lets the PostgreSQL schema run on SQLite unchanged). Environment
variables are set *before* importing the app so settings pick them up.
"""
import hashlib
import hmac
import os
import tempfile

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

WEBHOOK_SECRET = "test-secret"


def sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest_asyncio.fixture
async def client():
    # Fresh temp DB file per test for isolation.
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    os.environ["WEBHOOK_SECRET"] = WEBHOOK_SECRET
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{path}"
    os.environ["DESKLY_SEED"] = "false"

    # Import after env is set; clear settings cache in case of prior import.
    from app.config import get_settings

    get_settings.cache_clear()

    # Reload db and dependent modules so the engine uses the test DATABASE_URL.
    import importlib

    from app import db as db_module

    importlib.reload(db_module)
    from app import models as models_module

    importlib.reload(models_module)
    from app import bootstrap as bootstrap_module

    importlib.reload(bootstrap_module)
    from app.routers import tickets as tickets_module
    from app.routers import webhooks as webhooks_module

    importlib.reload(tickets_module)
    importlib.reload(webhooks_module)
    from app import main as main_module

    importlib.reload(main_module)

    app = main_module.app

    transport = ASGITransport(app=app)
    # Using the app as a context manager triggers lifespan (creates tables).
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        async with app.router.lifespan_context(app):
            yield ac

    db_module.engine.dispose()
    os.unlink(path)
