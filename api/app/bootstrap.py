"""Database bootstrap helpers: create tables and seed sample data.

For this prototype we create the schema from SQLAlchemy metadata on startup
instead of running Alembic migrations. Rationale (see DECISIONES.md): a single
initial schema with no production data to migrate makes full migration tooling
unnecessary overhead. Alembic is listed as a next step if the schema evolves.
"""
from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.enums import Prioridad
from app.models import Ticket


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


SAMPLE_TICKETS = [
    ("No puedo iniciar sesión", "El login devuelve 500.", Prioridad.alta, "ana"),
    ("Error al exportar CSV", "Se corta a 100 filas.", Prioridad.media, "luis"),
    ("Solicitud de nueva feature", "Modo oscuro, por favor.", Prioridad.baja, None),
]


async def seed() -> None:
    """Insert sample tickets if the table is empty (idempotent)."""
    async with SessionLocal() as session:
        existing = await session.scalar(select(Ticket).limit(1))
        if existing is not None:
            return
        for titulo, descripcion, prioridad, asignado in SAMPLE_TICKETS:
            session.add(
                Ticket(
                    titulo=titulo,
                    descripcion=descripcion,
                    prioridad=prioridad,
                    asignado_a=asignado,
                )
            )
        await session.commit()


async def init_db(with_seed: bool = True) -> None:
    await create_tables()
    if with_seed:
        await seed()
