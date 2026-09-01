"""
MÓDULO: main.py - Punto de entrada de la aplicación FastAPI

Este archivo configura y define la aplicación FastAPI principal de Deskly.
Aquí se definen:
- La aplicación FastAPI
- El ciclo de vida (startup/shutdown)
- Los middlewares (CORS)
- Los manejadores de excepciones
- Los endpoints de health check
- El registro de todos los routers

FastAPI es un framework moderno para construir APIs web en Python, similar a
Flask pero con validación automática de datos y documentación interactiva.
"""

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
    """
    Define el ciclo de vida de la aplicación.
    
    Ciclo de vida en FastAPI:
    - on_startup: se ejecuta cuando la app arranca
    - on_shutdown: se ejecuta cuando la app se detiene
    
    En este caso:
    - Al arrancar: ejecutamos la semilla (seed) de datos de ejemplo si está habilitada
    - Al arrancar: conectamos el WebSocket manager a Redis
    - Al detener: cerramos las conexiones
    
    La variable 'yield' marca el punto en que la app está lista para recibir requests.
    """
    # La semilla crea datos de ejemplo (usuarios, tickets) si no existen.
    # Se puede deshabilitar con DESKLY_SEED=false en las variables de entorno
    if os.getenv("DESKLY_SEED", "true").lower() != "false":
        await seed()
    
    # Conectamos el gestor de WebSocket a Redis para poder retransmitir eventos
    # a través de múltiples instancias. Si Redis no está disponible,
    # el manager funciona en modo local-only.
    await manager.startup(settings.redis_url)
    
    try:
        yield  # La app está lista para atender requests
    finally:
        # Al cerrar: limpiamos todas las conexiones
        await manager.shutdown()


# Creamos la aplicación FastAPI con un título y versión
# que aparecerán en la documentación automática (/docs)
app = FastAPI(title="Deskly API", version="1.0.0", lifespan=lifespan)

# MIDDLEWARE: CORS
# Permite que el frontend en localhost:3000 acceda a la API
# (sin CORS, los requests desde otro dominio serían bloqueados por el navegador)
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
    """
    Manejador personalizado para transiciones de estado inválidas.
    
    Cuando un usuario intenta cambiar un ticket a un estado no permitido,
    esta función intercepta la excepción InvalidTransitionError y devuelve
    una respuesta HTTP 409 (Conflict) con detalles útiles en lugar de un
    genérico 500 (Internal Server Error).
    
    Esto mejora la experiencia de la API: el cliente sabe exactamente
    qué salió mal y qué transiciones son válidas.
    """
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
    """
    Endpoint de verificación de salud extendida.
    
    Verifica que la aplicación y sus dependencias externas están funcionando:
    - "status": "ok" si todo va bien, "degraded" si hay problemas
    - "db": "ok" si la base de datos está accesible
    - "redis": "ok" si Redis está accesible, "not_configured" si no está habilitado
    
    Este endpoint es útil para:
    - Docker/Kubernetes: para saber si la instancia está lista
    - Monitoreo: para detectar problemas de conectividad
    - Debugging: para ver qué servicios están disponibles
    
    Devuelve:
        dict con el estado de la app y sus dependencias
    """
    from sqlalchemy import text

    from app.db import engine

    health_status = {"status": "ok"}

    # Verificar base de datos: ejecutamos un query simple (SELECT 1)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        health_status["db"] = "ok"
    except Exception:
        health_status["db"] = "error"
        health_status["status"] = "degraded"

    # Verificar Redis: usamos el ping del cliente de Redis
    if manager._redis is not None:
        try:
            await manager._redis.ping()
            health_status["redis"] = "ok"
        except Exception:
            health_status["redis"] = "error"
            health_status["status"] = "degraded"
    else:
        # Redis es opcional: si no está configurado, no es un error
        health_status["redis"] = "not_configured"

    return health_status


# Registramos todos los routers (módulos de endpoints)
# Cada router define un conjunto de endpoints relacionados (ej: auth, tickets, usuarios)
app.include_router(auth.router)
app.include_router(user_options.router)
app.include_router(users.router)
app.include_router(tickets.router)
app.include_router(webhooks.router)
app.include_router(websocket.router)
