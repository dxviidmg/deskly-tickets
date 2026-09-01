"""
MÓDULO: ws.py - Gestor de WebSocket con fan-out vía Redis pub/sub

WebSocket: conexión bidireccional entre cliente y servidor en tiempo real.

Arquitectura:
- Cada cliente conectado abre un WebSocket /ws/tickets
- Los eventos (ticket creado, actualizado, etc.) se publican vía Redis
- Redis distribuye el evento a todas las instancias
- Cada instancia envía el evento a sus clientes WebSocket locales

¿Por qué Redis?
- Si la app tiene múltiples instancias (replicas, load balancer):
  Un cliente conectado a instancia A no vería eventos de instancia B
- Redis pub/sub permite que todas las instancias compartan eventos
- Si no hay Redis: funciona en local-only (solo eventos de la misma instancia)

Flujo de un evento:
1. Router: await manager.broadcast(DomainEvent.TICKET_CREATED, ticket)
2. manager.broadcast() publica en Redis
3. _reader() (tarea en background) recibe del Redis
4. _broadcast_local() envía a todas las conexiones WebSocket activas

Manejo de desconexiones:
- Si un cliente se desconecta, lo eliminamos del conjunto
- Si falla enviar a un cliente, lo marcamos como muerto y lo eliminamos
"""

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder

logger = logging.getLogger("deskly.ws")

# Nombre del canal Redis donde se publican eventos
EVENTS_CHANNEL = "deskly:events"


class ConnectionManager:
    """
    Gestiona todas las conexiones WebSocket y el broadcast de eventos.
    
    Responsabilidades:
    - Aceptar/rechazar conexiones WebSocket
    - Enviar eventos a clientes conectados
    - Sincronizar eventos a través de Redis (multi-instancia)
    - Limpieza de conexiones muertas
    
    Atributos:
    - _connections: conjunto de WebSocket activas (locales)
    - _redis: cliente Redis (puede ser None si no está configurado)
    - _pubsub: suscripción a Redis
    - _reader_task: tarea de background que escucha Redis
    - _lock: candado para acceso thread-safe a _connections
    """

    def __init__(self) -> None:
        """Inicializa el gestor con conjuntos y referencias vacías."""
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._redis: Any | None = None
        self._pubsub: Any | None = None
        self._reader_task: asyncio.Task | None = None

    # ========== CICLO DE VIDA ==========

    async def startup(self, redis_url: str | None) -> None:
        """
        Conecta a Redis e inicia el suscriptor.
        
        Se llama al arrancar la app (desde main.py en lifespan()).
        
        Tolerancia a fallos:
        - Si Redis no está configurado (redis_url=None): modo local-only
        - Si Redis no es alcanzable: log warning, modo local-only
        
        Args:
            redis_url (str | None): URL de Redis (ej: redis://localhost:6379/0)
                                    None significa que no usamos Redis
        """
        if not redis_url:
            logger.info("No REDIS_URL set; WebSocket runs in local-only mode.")
            return
        
        try:
            # Importar el cliente de Redis
            import redis.asyncio as aioredis

            # Conectar a Redis
            self._redis = aioredis.from_url(redis_url, decode_responses=True)
            
            # Verificar que Redis responde (fail fast)
            await self._redis.ping()
            
            # Crear una suscripción al canal de eventos
            self._pubsub = self._redis.pubsub()
            await self._pubsub.subscribe(EVENTS_CHANNEL)
            
            # Iniciar tarea de background que escucha Redis
            self._reader_task = asyncio.create_task(self._reader())
            
            logger.info("Connected to Redis pub/sub for WebSocket fan-out.")
        except Exception as exc:  # pragma: no cover - depends on environment
            # Redis no disponible: funcionar en modo degradado
            logger.warning(
                "Redis unavailable (%s); falling back to local-only broadcast.",
                exc,
            )
            self._redis = None
            self._pubsub = None

    async def shutdown(self) -> None:
        """
        Cierra todas las conexiones y detiene los procesos en background.
        
        Se llama al apagar la app (desde main.py en lifespan()).
        
        Limpia:
        - Tarea de background (_reader)
        - Suscripción Redis
        - Conexión Redis
        """
        # Cancelar la tarea de lectura de Redis
        if self._reader_task is not None:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except (asyncio.CancelledError, Exception):
                pass
            self._reader_task = None
        
        # Cerrar suscripción Redis
        if self._pubsub is not None:
            try:
                await self._pubsub.unsubscribe(EVENTS_CHANNEL)
                await self._pubsub.aclose()
            except Exception:
                pass
            self._pubsub = None
        
        # Cerrar conexión Redis
        if self._redis is not None:
            try:
                await self._redis.aclose()
            except Exception:
                pass
            self._redis = None

    # ========== CONEXIONES ==========

    async def connect(self, websocket: WebSocket) -> None:
        """
        Acepta una nueva conexión WebSocket.
        
        Se llama cuando un cliente se conecta a /ws/tickets
        
        Args:
            websocket (WebSocket): La conexión nuevo del cliente
        """
        # Aceptar la conexión (handshake WebSocket)
        await websocket.accept()
        
        # Agregar a nuestro conjunto de conexiones activas
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        """
        Elimina una conexión WebSocket.
        
        Se llama cuando:
        - El cliente cierra la conexión
        - La conexión se corta (timeout, error, etc.)
        - Un error ocurre al enviar
        
        Args:
            websocket (WebSocket): La conexión a eliminar
        """
        async with self._lock:
            self._connections.discard(websocket)

    # ========== PUBLICACIÓN / BROADCAST ==========

    async def broadcast(self, tipo: str, datos: Any) -> None:
        """
        Publica un evento para que todas las instancias lo retransmitan.
        
        Llamado desde los routers cuando algo importante ocurre:
            await manager.broadcast(DomainEvent.TICKET_CREATED, ticket_out)
        
        Comportamiento:
        - Con Redis: publica en el canal, otras instancias lo reciben
        - Sin Redis: envía directamente a conexiones locales
        
        Args:
            tipo (str): Tipo de evento (ej: "ticket.creado")
            datos (Any): Datos a enviar (ej: TicketOut, diccionario)
        """
        # Construir mensaje
        message = {
            "tipo": tipo,
            "datos": jsonable_encoder(datos)  # Convierte a JSON serializable
        }
        
        # Si tenemos Redis: publicar en el canal
        if self._redis is not None:
            try:
                await self._redis.publish(EVENTS_CHANNEL, json.dumps(message))
                return
            except Exception as exc:  # pragma: no cover
                logger.warning("Redis publish failed (%s); broadcasting local.", exc)
        
        # Fallback: broadcast local directo
        await self._broadcast_local(message)

    async def _reader(self) -> None:
        """
        Tarea de background: escucha Redis y retransmite a conexiones locales.
        
        Proceso:
        1. Listen() espera indefinidamente por mensajes en el canal
        2. Cuando llega un mensaje, deserializar JSON
        3. Enviar a todas las conexiones locales
        4. Si se cancela (shutdown), salir limpiamente
        
        Esta tarea corre mientras la app está activa.
        """
        assert self._pubsub is not None
        try:
            async for message in self._pubsub.listen():
                # Ignorar mensajes no-data (subscribe confirmations, etc.)
                if message.get("type") != "message":
                    continue
                
                # Deserializar el payload
                try:
                    payload = json.loads(message["data"])
                except (ValueError, TypeError):
                    # JSON inválido, saltar
                    continue
                
                # Retransmitir a conexiones locales
                await self._broadcast_local(payload)
        except asyncio.CancelledError:  # pragma: no cover
            raise
        except Exception as exc:  # pragma: no cover
            logger.warning("Redis subscriber stopped: %s", exc)

    async def _broadcast_local(self, message: dict) -> None:
        """
        Envía un mensaje a todas las conexiones WebSocket locales.
        
        Si una conexión falla:
        - La eliminamos de _connections (dead socket)
        - No bloqueamos a otros clientes
        
        Args:
            message (dict): Mensaje a enviar (con "tipo" y "datos")
        """
        # Tomar copia de conexiones (para evitar mutation durante iteración)
        async with self._lock:
            targets = list(self._connections)

        # Intentar enviar a cada conexión
        dead: list[WebSocket] = []
        for connection in targets:
            try:
                await connection.send_json(message)
            except Exception:
                # Conexión muerta, marcar para eliminar
                dead.append(connection)

        # Eliminar conexiones muertas del conjunto
        if dead:
            async with self._lock:
                for connection in dead:
                    self._connections.discard(connection)


# Instancia global del manager
# Se importa en main.py, routers y otros módulos
manager = ConnectionManager()
