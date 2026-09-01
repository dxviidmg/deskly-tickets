"""Database bootstrap helpers.

The schema is managed by Alembic migrations (run via `alembic upgrade head`
before the app starts; see the Docker entrypoint and README). This module only
provides an idempotent seed used on startup for the prototype: 10 users (an
initial admin plus sample agents) and a few sample tickets.
"""
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.enums import Prioridad
from app.models import Ticket, User
from app.security import hash_password

settings = get_settings()


# Sample users seeded on startup (besides the admin from settings).
# Each tuple: (email, password, nombre, apellidos, is_admin).
SAMPLE_USERS: list[tuple[str, str, str, str, bool]] = [
    ("agente@deskly.com", "agente123", "Agente", "Soporte", False),
    ("victor@deskly.com", "victor123", "Victor", "Hernandez", False),
    ("lucia@deskly.com", "lucia123", "Lucia", "Gomez", False),
    ("mateo@deskly.com", "mateo123", "Mateo", "Fernandez", False),
    ("sofia@deskly.com", "sofia123", "Sofia", "Martinez", False),
    ("diego@deskly.com", "diego123", "Diego", "Ramirez", False),
    ("valentina@deskly.com", "valentina123", "Valentina", "Torres", False),
    ("javier@deskly.com", "javier123", "Javier", "Ruiz", False),
    ("camila@deskly.com", "camila123", "Camila", "Morales", True),
]


async def seed() -> None:
    """Create the admin user, sample agents and sample tickets (idempotent).

    Seeds 10 users in total: the admin from settings plus the entries in
    ``SAMPLE_USERS``. Every insert is guarded by an email lookup so running
    the seed repeatedly is safe.
    """
    async with SessionLocal() as session:
        # --- Admin user (from settings) ---
        admin = await session.scalar(
            select(User).where(User.email == settings.admin_email)
        )
        if admin is None:
            admin = User(
                email=settings.admin_email,
                hashed_password=hash_password(settings.admin_password),
                nombre="Admin",
                apellidos="Deskly",
                is_admin=True,
            )
            session.add(admin)

        # --- Sample users (idempotent by email) ---
        for email, password, nombre, apellidos, is_admin in SAMPLE_USERS:
            existing_user = await session.scalar(
                select(User).where(User.email == email)
            )
            if existing_user is None:
                session.add(
                    User(
                        email=email,
                        hashed_password=hash_password(password),
                        nombre=nombre,
                        apellidos=apellidos,
                        is_admin=is_admin,
                    )
                )

        await session.commit()
        await session.refresh(admin)

        # The first sample agent is used to assign the sample tickets below.
        agent = await session.scalar(
            select(User).where(User.email == "agente@deskly.com")
        )

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
