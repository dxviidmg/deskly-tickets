"""WebSocket connection manager with Redis pub/sub fan-out.

Each backend process keeps its own set of live WebSocket connections (that is
inherent to WebSockets). To make events reach clients connected to *any*
instance, events are published to a Redis channel; a background subscriber in
every instance receives them and relays them to its local connections.

Redis is optional for local/test runs: if it is not configured or not
reachable, the manager falls back to broadcasting directly to local
connections, so the app (and the test suite) works without Redis.
"""
import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder

logger = logging.getLogger("deskly.ws")

EVENTS_CHANNEL = "deskly:events"


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._redis: Any | None = None
        self._pubsub: Any | None = None
        self._reader_task: asyncio.Task | None = None

    # --- lifecycle -------------------------------------------------------

    async def startup(self, redis_url: str | None) -> None:
        """Connect to Redis and start the subscriber. No-op/fallback on error."""
        if not redis_url:
            logger.info("No REDIS_URL set; WebSocket runs in local-only mode.")
            return
        try:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(redis_url, decode_responses=True)
            # Fail fast if Redis is unreachable.
            await self._redis.ping()
            self._pubsub = self._redis.pubsub()
            await self._pubsub.subscribe(EVENTS_CHANNEL)
            self._reader_task = asyncio.create_task(self._reader())
            logger.info("Connected to Redis pub/sub for WebSocket fan-out.")
        except Exception as exc:  # pragma: no cover - depends on environment
            logger.warning(
                "Redis unavailable (%s); falling back to local-only broadcast.",
                exc,
            )
            self._redis = None
            self._pubsub = None

    async def shutdown(self) -> None:
        if self._reader_task is not None:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except (asyncio.CancelledError, Exception):
                pass
            self._reader_task = None
        if self._pubsub is not None:
            try:
                await self._pubsub.unsubscribe(EVENTS_CHANNEL)
                await self._pubsub.aclose()
            except Exception:
                pass
            self._pubsub = None
        if self._redis is not None:
            try:
                await self._redis.aclose()
            except Exception:
                pass
            self._redis = None

    # --- connections -----------------------------------------------------

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    # --- publishing / broadcasting --------------------------------------

    async def broadcast(self, tipo: str, datos: Any) -> None:
        """Publish an event so every instance can relay it to its clients.

        With Redis: publish to the channel; the subscriber (here and in other
        instances) delivers it locally. Without Redis: deliver locally now.
        """
        message = {"tipo": tipo, "datos": jsonable_encoder(datos)}
        if self._redis is not None:
            try:
                await self._redis.publish(EVENTS_CHANNEL, json.dumps(message))
                return
            except Exception as exc:  # pragma: no cover
                logger.warning("Redis publish failed (%s); broadcasting local.", exc)
        await self._broadcast_local(message)

    async def _reader(self) -> None:
        """Background task: relay messages from Redis to local connections."""
        assert self._pubsub is not None
        try:
            async for message in self._pubsub.listen():
                if message.get("type") != "message":
                    continue
                try:
                    payload = json.loads(message["data"])
                except (ValueError, TypeError):
                    continue
                await self._broadcast_local(payload)
        except asyncio.CancelledError:  # pragma: no cover
            raise
        except Exception as exc:  # pragma: no cover
            logger.warning("Redis subscriber stopped: %s", exc)

    async def _broadcast_local(self, message: dict) -> None:
        """Send a ready message to every locally connected client.

        Connections that fail are dropped so a dead client never blocks the
        others and never raises silent errors.
        """
        async with self._lock:
            targets = list(self._connections)

        dead: list[WebSocket] = []
        for connection in targets:
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)

        if dead:
            async with self._lock:
                for connection in dead:
                    self._connections.discard(connection)


manager = ConnectionManager()
