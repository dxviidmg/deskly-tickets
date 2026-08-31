"""FastAPI application entrypoint."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.bootstrap import init_db
from app.config import get_settings
from app.routers import tickets, webhooks, websocket
from app.state_machine import InvalidTransitionError

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create schema (and seed sample data unless disabled) on startup.
    with_seed = os.getenv("DESKLY_SEED", "true").lower() != "false"
    await init_db(with_seed=with_seed)
    yield


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


app.include_router(tickets.router)
app.include_router(webhooks.router)
app.include_router(websocket.router)
