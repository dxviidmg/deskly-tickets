"""Gestor de conexiones WebSocket con fan-out via Redis pub/sub.

Cada proceso del backend mantiene su propio conjunto de conexiones WebSocket
activas (es inherente a WebSockets). Para que los eventos lleguen a clientes
conectados a cualquier instancia, se publican en un canal Redis; un suscriptor
en segundo plano en cada instancia los recibe y los retransmite a sus conexiones
locales.

Redis es opcional para ejecuciones locales/tests: si no está configurado o no
está accesible, el gestor hace broadcast directamente a las conexiones locales,
así la app (y la suite de tests) funciona sin Redis.
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
    """Gestiona las conexiones WebSocket y el broadcast de eventos.
    
    Métodos principales:
    - startup: Conectar a Redis e iniciar el suscriptor
    - shutdown: Cerrar conexiones y detener el suscriptor
    - connect: Aceptar una nueva conexión WebSocket
    - disconnect: Eliminar una conexión
    - broadcast: Enviar un evento a todos los clientes conectados
    """

    def __init__(self) -> None:
        """Inicializa el gestor con conjuntos vacíos."""
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._redis: Any | None = None
        self._pubsub: Any | None = None
        self._reader_task: asyncio.Task | None = None

    # --- ciclo de vida ---------------------------------------------------

    async def startup(self, redis_url: str | None) -> None:
        """Conecta a Redis e inicia el suscriptor. No-op si no hay Redis.
        
        Si Redis no está disponible, el gestor funciona en modo local-only.
        """
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
        """Cierra todas las conexiones y detiene el suscriptor de Redis."""
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

    # --- conexiones ------------------------------------------------------

    async def connect(self, websocket: WebSocket) -> None:
        """Acepta una nueva conexión WebSocket y la añade al conjunto."""
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        """Elimina una conexión del conjunto (el cliente se desconectó)."""
        async with self._lock:
            self._connections.discard(websocket)

    # --- publicación / broadcast ----------------------------------------

    async def broadcast(self, tipo: str, datos: Any) -> None:
        """Publica un evento para que todas las instancias lo retransmitan.
        
        Con Redis: publica en el canal; el suscriptor (aquí y en otras
        instancias) lo entrega localmente. Sin Redis: entrega local directamente.
        
        Args:
            tipo: Tipo de evento (DomainEvent)
            datos: Datos del evento (normalmente un TicketOut)
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
        """Tarea en segundo plano: retransmite mensajes de Redis a conexiones locales."""
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
        """Envía un mensaje a todos los clientes conectados localmente.
        
        Las conexiones que fallan se eliminan para que un cliente muerto
        nunca bloquee a los demás ni lance errores silenciosos.
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
