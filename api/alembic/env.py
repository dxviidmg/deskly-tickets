"""
ARCHIVO: alembic/env.py
PROPÓSITO: Configuración de Alembic para migraciones de BD

Alembic es una herramienta que gestiona cambios en el esquema de BD.

¿Qué es una migración?
Un script que describe cómo cambiar la BD de la versión X a versión X+1.

Ejemplo:
    Versión 1: tabla users (id, email)
    Cambio necesario: agregar columna 'nombre'
    → Se crea un script de migración (0002_add_nombre.py)
    → Al ejecutar: alembic upgrade head
    → Se crea la columna automáticamente en la BD

¿Por qué Alembic?
- Reproducibilidad: cualquiera puede pasar de BD v1 a v1 ejecutando migraciones
- Historial: se ve quién hizo qué cambio y cuándo
- Rollback: se puede deshacer una migración si algo sale mal
- Seguridad: se revisan cambios de esquema en PR antes de aplicar

Configuración de env.py:
- Lee DATABASE_URL de app/config.py (única fuente de verdad, no hardcoded)
- Usa SQLAlchemy en modo asincrónico
- Detecta cambios en los modelos (autogenerate)
- Aplica migraciones tanto offline como online
"""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy.pool import NullPool

from app.db import Base

# Importar modelos para que se registren en Base.metadata
# (sin esto, alembic no sabría qué tablas existen)
import app.models  # noqa: F401

# Obtener configuración de Alembic (desde alembic.ini)
config = context.config

# Configurar logging si existe logging.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inyectar DATABASE_URL desde variable de entorno
# Usamos os.environ directamente para evitar que Pydantic lea del .env local
# En Docker, la variable viene de docker-compose.yml
# En desarrollo local, puede venir de .env o del entorno
database_url = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://deskly:deskly@db:5432/deskly"
)
config.set_main_option("sqlalchemy.url", database_url)

# Metadata: información del esquema de BD (tablas, columnas, índices)
# Alembic lo usa para detectar cambios
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Ejecutar migraciones en modo offline.
    
    Offline significa: no se conecta a la BD real, solo genera SQL.
    Útil para:
    - Revisar qué SQL se ejecutará
    - Generar script SQL para ejecutar manualmente
    - Entornos donde no hay acceso directo a la BD (CI/CD)
    
    Proceso:
    1. Obtener DATABASE_URL
    2. Configurar contexto sin conexión
    3. Ejecutar migraciones (genera SQL)
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,  # Binds los parámetros en el SQL
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # Comparar tipos de columnas exactamente
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """
    Función auxiliar: ejecutar migraciones con una conexión real.
    
    Se llama desde run_migrations_online() para aplicar los cambios
    a la BD de verdad.
    
    Args:
        connection: Conexión SQLAlchemy sincrónica a la BD
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Ejecutar migraciones en modo online (contra BD real).
    
    Online significa: conecta a la BD y ejecuta cambios inmediatamente.
    Normalmente es lo que se usa en desarrollo y producción.
    
    ¿Por qué async?
    - FastAPI usa asyncio (async/await)
    - SQLAlchemy soporta async (más eficiente que sync)
    - Las migraciones se ejecutan desde entrypoint.sh (async compatible)
    
    Proceso:
    1. Crear engine asincrónico desde config
    2. Conectar a la BD
    3. Ejecutar migraciones
    4. Cerrar conexión
    """
    # Crear motor async desde config
    # poolclass=NullPool: no reutilizar conexiones (mejor para migraciones puntuales)
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=NullPool,
    )
    
    # Conectar y ejecutar
    async with connectable.connect() as connection:
        # run_sync: ejecutar función sincrónica dentro del contexto async
        await connection.run_sync(do_run_migrations)
    
    # Cerrar el motor (liberar resources)
    await connectable.dispose()


# Punto de entrada: detectar si es offline u online y ejecutar
if context.is_offline_mode():
    # Offline: generar SQL sin conectar
    run_migrations_offline()
else:
    # Online: conectar y aplicar
    asyncio.run(run_migrations_online())
