"""Database bootstrap helpers.

The schema is managed by Alembic migrations (run via `alembic upgrade head`
before the app starts; see the Docker entrypoint and README). This module only
provides an idempotent seed used on startup for the prototype: 10 users (an
initial admin plus sample agents) and 100 sample tickets with varied states
and priorities.

Instead of inserting each ticket directly in its final state, the seed makes
every ticket **walk through its lifecycle** from ``abierto`` up to its target
state. For each state change it inserts a ``state_log`` entry and a matching
``comment`` narrating the change, with timestamps staggered by one minute so the
history reads like it was produced by real API usage.

Timestamps are controlled explicitly, so ticket/state_log/comment rows are
written with Core ``insert(...)`` statements (which do NOT fire the ORM event
listeners in ``app.events`` that would otherwise stamp ``creado_en = now()``).
"""
import random
from datetime import datetime, timedelta

from sqlalchemy import insert, select

from app.config import get_settings
from app.db import SessionLocal
from app.enums import Estado, Prioridad
from app.models import Comment, StateLog, Ticket, User
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

# Author used for system-generated comments when a ticket is unassigned.
SYSTEM_AUTHOR = "sistema@deskly.com"

# One minute between each state change, so the history is ordered and realistic.
STEP = timedelta(minutes=1)

# Lifecycle path each ticket walks to reach its target state. Every path starts
# at ``abierto`` (the initial state) and follows the documented state machine:
# abierto -> en_progreso -> resuelto -> {cerrado, reabierto}.
LIFECYCLE_PATHS: dict[Estado, list[Estado]] = {
    Estado.abierto: [Estado.abierto],
    Estado.en_progreso: [Estado.abierto, Estado.en_progreso],
    Estado.resuelto: [Estado.abierto, Estado.en_progreso, Estado.resuelto],
    Estado.cerrado: [
        Estado.abierto,
        Estado.en_progreso,
        Estado.resuelto,
        Estado.cerrado,
    ],
    Estado.reabierto: [
        Estado.abierto,
        Estado.en_progreso,
        Estado.resuelto,
        Estado.reabierto,
    ],
}

# Human-readable comment body for each state a ticket transitions into.
STEP_COMMENTS: dict[Estado, str] = {
    Estado.abierto: "Ticket creado y a la espera de un agente.",
    Estado.en_progreso: "Empezamos a trabajar en el ticket.",
    Estado.resuelto: "Aplicamos una solución; queda pendiente de confirmación.",
    Estado.cerrado: "Confirmada la solución. Cerramos el ticket.",
    Estado.reabierto: "El problema reapareció, reabrimos el ticket.",
}


async def seed() -> None:
    """Create the admin user, sample agents and sample tickets (idempotent).

    Seeds 10 users in total: the admin from settings plus the entries in
    ``SAMPLE_USERS``. Every insert is guarded by an email lookup so running
    the seed repeatedly is safe. Tickets are only seeded when the table is
    empty; each one walks its lifecycle, logging a ``state_log`` and a
    ``comment`` per change with one-minute steps.
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

        # --- Sample tickets (only if none exist) ---
        existing = await session.scalar(select(Ticket).limit(1))
        if existing is not None:
            return

        # Map user id -> email so comments can be attributed to the assignee.
        users = (await session.scalars(select(User))).all()
        email_by_id = {u.id: u.email for u in users}
        user_ids = sorted(email_by_id)
        assignees: list[int | None] = [*user_ids, None]

        estados = list(Estado)
        prioridades = list(Prioridad)
        asuntos = [
            "No puedo iniciar sesión",
            "Error al exportar CSV",
            "La página carga muy lenta",
            "Solicitud de nueva feature",
            "Fallo al subir archivos adjuntos",
            "El correo de notificación no llega",
            "Error 500 al guardar el formulario",
            "Problema con el pago",
            "La búsqueda no devuelve resultados",
            "Se pierde la sesión al recargar",
            "El dashboard muestra datos incorrectos",
            "No se aplican los filtros",
        ]

        # Deterministic pseudo-random data across restarts.
        rng = random.Random(42)

        # Base moment for the whole seed; each ticket starts a bit later so
        # their histories don't all collapse onto the same instant.
        base = datetime.now() - timedelta(days=len(asuntos))

        for i in range(100):
            # Cycle through states and priorities so every combination is
            # represented, then add variety with the subject/assignee.
            estado = estados[i % len(estados)]
            prioridad = prioridades[i % len(prioridades)]
            asunto = asuntos[i % len(asuntos)]
            
            # For "abierto" tickets: 50% assigned, 50% unassigned (alternating by i).
            # For other states: always assign a user (no None).
            if estado == Estado.abierto:
                # Even indices: assigned; odd indices: unassigned.
                asignado_id = rng.choice(user_ids) if (i % 2) == 0 else None
            else:
                # Tickets in progress/resolved/closed must have an assignee.
                asignado_id = rng.choice(user_ids)
            
            autor = email_by_id.get(asignado_id, SYSTEM_AUTHOR)

            path = LIFECYCLE_PATHS[estado]
            # Stagger tickets so their creation moments differ.
            ticket_created = base + timedelta(minutes=i * len(estados))
            # The ticket's own timestamps reflect creation and the last change.
            last_change_at = ticket_created + STEP * (len(path) - 1)

            ticket_id = await session.scalar(
                insert(Ticket)
                .values(
                    titulo=f"{asunto} (#{i + 1})",
                    descripcion=(
                        f"Ticket de ejemplo número {i + 1}. "
                        f"Estado final: {estado.value}, "
                        f"prioridad: {prioridad.value}."
                    ),
                    estado=estado.value,
                    prioridad=prioridad.value,
                    asignado_a_id=asignado_id,
                    creado_en=ticket_created,
                    actualizado_en=last_change_at,
                )
                .returning(Ticket.id)
            )

            # Walk the lifecycle: one state_log + one comment per change,
            # staggered by one minute starting at the ticket's creation.
            for step_index, nuevo_estado in enumerate(path):
                changed_at = ticket_created + STEP * step_index
                await session.execute(
                    insert(StateLog),
                    {
                        "ticket_id": ticket_id,
                        "mensaje": f"Cambio de status: {nuevo_estado.value}",
                        "usuario_id": asignado_id,
                        "creado_en": changed_at,
                    },
                )
                await session.execute(
                    insert(Comment),
                    {
                        "ticket_id": ticket_id,
                        "autor": autor,
                        "cuerpo": STEP_COMMENTS[nuevo_estado],
                        "creado_en": changed_at,
                    },
                )

        await session.commit()
