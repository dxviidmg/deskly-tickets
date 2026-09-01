"""
MÓDULO: db.py - Motor de base de datos y sesiones

Este archivo configura la conexión asíncrona a PostgreSQL y proporciona
las herramientas que toda la aplicación usa para acceder a la base de datos.

Conceptos clave:
- Engine: la conexión al servidor de PostgreSQL
- SessionLocal: factory que crea sesiones (transacciones aisladas)
- Base: clase base para todos los modelos ORM (Object-Relational Mapping)

SQLAlchemy es un ORM: permite trabajar con la BD usando clases Python
en lugar de escribir SQL directamente.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# ========== ENGINE ==========
# Crea la conexión al servidor PostgreSQL
# - create_async_engine: crea un engine asíncrono (no bloquea threads)
# - settings.database_url: la URL de conexión (ej: postgresql+asyncpg://usuario:pass@host/db)
# - echo=False: no imprime SQL en consola (útil para debugging si es True)
# - future=True: usa la API más nueva de SQLAlchemy 2.0
engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True
)

# ========== SESSION FACTORY ==========
# Crea un factory que genera sesiones cuando las necesitamos
# - AsyncSession: sesión asíncrona que no bloquea
# - expire_on_commit=False: los objetos mantienen sus datos después de commit
#   (por defecto SQLAlchemy los descarga para asegurar consistencia)
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    """
    Clase base para todos los modelos ORM.
    
    Todos los modelos de la aplicación (User, Ticket, Comment, etc.)
    heredan de esta clase. SQLAlchemy usa esta clase para:
    - Saber que es un modelo ORM
    - Mapear la clase a tablas de la BD
    - Generar las migraciones (via Alembic)
    """
    pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependencia de FastAPI que proporciona una sesión de BD.
    
    Se usa así en los routers:
        @router.get("/tickets")
        async def list_tickets(session: AsyncSession = Depends(get_session)):
            tickets = await session.scalars(select(Ticket))
            return tickets
    
    FastAPI llama a esta función automáticamente:
    1. Crea una sesión nueva
    2. La pasa al handler del endpoint
    3. La cierra después (en el finally)
    
    Yield es como return pero permite ejecutar código después del endpoint.
    Es util para cleanup/cierre de recursos.
    
    Yields:
        Una sesión AsyncSession nueva para cada request
    """
    async with SessionLocal() as session:
        yield session
