"""In-memory WebSocket connection manager and event broadcasting.

The manager keeps the set of active connections in process memory. This is
enough for a single-process deployment. Scaling to multiple workers would
require an external pub/sub (e.g. Redis); documented as out of scope.
"""
import asyncio
from typing import Any

from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, tipo: str, datos: Any) -> None:
        """Send an event to every connected client.

        Any connection that fails to receive the message is dropped, so a dead
        client never blocks the others and never raises silent errors.
        """
        message = {"tipo": tipo, "datos": jsonable_encoder(datos)}
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
