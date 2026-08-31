"""Database bootstrap helpers.

The schema is managed by Alembic migrations (run via `alembic upgrade head`
before the app starts; see the Docker entrypoint and README). This module only
provides an idempotent seed used on startup for the prototype: an initial admin
user, a sample agent and a few sample tickets.
"""
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.enums import Prioridad
from app.models import Ticket, User
from app.security import hash_password

settings = get_settings()


async def seed() -> None:
    """Create the admin user, a sample agent and sample tickets (idempotent)."""
    async with SessionLocal() as session:
        # --- Admin user (from settings) ---
        admin = await session.scalar(
            select(User).where(User.email == settings.admin_email)
        )
        if admin is None:
            admin = User(
                email=settings.admin_email,
                hashed_password=hash_password(settings.admin_password),
                is_admin=True,
            )
            session.add(admin)

        # --- Sample non-admin agent ---
        agent = await session.scalar(
            select(User).where(User.email == "agente@deskly.com")
        )
        if agent is None:
            agent = User(
                email="agente@deskly.com",
                hashed_password=hash_password("agente123"),
                is_admin=False,
            )
            session.add(agent)

        await session.commit()
        await session.refresh(admin)
        await session.refresh(agent)

        # --- Sample tickets (only if none exist) ---
        existing = await session.scalar(select(Ticket).limit(1))
        if existing is None:
            samples = [
                ("No puedo iniciar sesión", "El login devuelve 500.", Prioridad.alta, agent.id),
                ("Error al exportar CSV", "Se corta a 100 filas.", Prioridad.media, agent.id),
                ("Solicitud de nueva feature", "Modo oscuro, por favor.", Prioridad.baja, None),
            ]
            for titulo, descripcion, prioridad, asignado_id in samples:
                session.add(
                    Ticket(
                        titulo=titulo,
                        descripcion=descripcion,
                        prioridad=prioridad,
                        asignado_a_id=asignado_id,
                    )
                )
            await session.commit()
