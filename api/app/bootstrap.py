"""Database bootstrap helpers.

The schema is managed by Alembic migrations (run via `alembic upgrade head`
before the app starts; see the Docker entrypoint and README). This module only
provides an idempotent sample-data seed used on startup for the prototype.
"""
from sqlalchemy import select

from app.db import SessionLocal
from app.enums import Prioridad
from app.models import Ticket

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
