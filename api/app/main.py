"""FastAPI application entrypoint."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.bootstrap import seed
from app.config import get_settings
from app.events import receive_ticket_after_insert, receive_ticket_after_update  # noqa: F401
from app.routers import auth, tickets, user_options, users, webhooks, websocket
from app.state_machine import InvalidTransitionError
from app.ws import manager

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is created by Alembic migrations before startup. Here we only seed
    # sample data unless disabled (DESKLY_SEED=false).
    if os.getenv("DESKLY_SEED", "true").lower() != "false":
        await seed()
    # Connect the WebSocket manager to Redis (falls back to local-only if the
    # broker is not reachable).
    await manager.startup(settings.redis_url)
    try:
        yield
    finally:
        await manager.shutdown()


app = FastAPI(title="Deskly API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(InvalidTransitionError)
async def invalid_transition_handler(
    request: Request, exc: InvalidTransitionError
) -> JSONResponse:
    """Map invalid state transitions to a clear 409 (never a generic 500)."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "detail": {
                "mensaje": "Transición de estado inválida",
                "actual": exc.current.value,
                "solicitado": exc.requested.value,
                "permitidas": exc.allowed,
            }
        },
    )


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(user_options.router)
app.include_router(users.router)
app.include_router(tickets.router)
app.include_router(webhooks.router)
app.include_router(websocket.router)
