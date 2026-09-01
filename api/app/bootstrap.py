"""
MÓDULO: bootstrap.py - Inicialización de datos de ejemplo

Este módulo crea datos iniciales (seed) cuando la app arranca.

¿Para qué?
- En desarrollo: tener datos para probar la UI
- En tests: tener datos conocidos sin ejecutar fixtures complicadas
- En producción: crear el usuario admin inicial

¿Qué se crea?
1. Usuario administrador (de config.py)
2. Usuarios de ejemplo (agentes de soporte)
3. 100 tickets de ejemplo en varios estados

¿Cómo se diferencia de migraciones?
- Alembic (alembic upgrade head): crea ESQUEMA (tablas, índices)
- bootstrap.seed(): crea DATOS de ejemplo

¿Por qué hacemos "walk through the lifecycle"?
Cada ticket imaginario CAMBIA DE ESTADO a lo largo de su vida simulada,
no se crea directamente en su estado final. Esto permite:
- Crear históricos realistas (state_log con comentarios)
- Probar que el timeline funciona
- Demostrar cómo se ve un ticket "antiguo" vs. "reciente"

Ejemplo:
    Ticket #5 (estado final: "resuelto")
    - Creado hace 3 horas en "abierto"
    - Cambió a "en_progreso" hace 2 horas
    - Cambió a "resuelto" hace 1 hora
    - (No fue cerrado porque es un ejemplo de "waiting for confirmation")

Timestamps escalonados:
- BaseTime: hace N días
- Cada ticket: +1 minuto entre cambios de estado
- Así el histórico se ve real (no todo pasó en el segundo 0)
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


# ========== USUARIOS DE EJEMPLO ==========
# Tuplas: (email, contraseña, nombre, apellidos, es_admin)
# Además del admin (de config.py), creamos 9 agentes de soporte
SAMPLE_USERS: list[tuple[str, str, str, str, bool]] = [
    ("agente@deskly.com", "agente123", "Agente", "Soporte", False),
    ("victor@deskly.com", "victor123", "Victor", "Hernandez", False),
    ("lucia@deskly.com", "lucia123", "Lucia", "Gomez", False),
    ("mateo@deskly.com", "mateo123", "Mateo", "Fernandez", False),
    ("sofia@deskly.com", "sofia123", "Sofia", "Martinez", False),
    ("diego@deskly.com", "diego123", "Diego", "Ramirez", False),
    ("valentina@deskly.com", "valentina123", "Valentina", "Torres", False),
    ("javier@deskly.com", "javier123", "Javier", "Ruiz", False),
    ("camila@deskly.com", "camila123", "Camila", "Morales", True),  # Camila es también admin
]

# Autor usado para comentarios generados por el sistema
SYSTEM_AUTHOR = "sistema@deskly.com"

# Intervalo entre cambios de estado (en minutos)
# Si es 1 minuto, cada transición ocurre 1 minuto después de la anterior
STEP = timedelta(minutes=1)

# Caminos de ciclo de vida: para cada estado final, qué estados atravesar
# Permite que los tickets "caminen" por su historia de forma realista
LIFECYCLE_PATHS: dict[Estado, list[Estado]] = {
    Estado.abierto: [Estado.abierto],  # Nunca avanza
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

# Mensaje amigable para cada cambio de estado
STEP_COMMENTS: dict[Estado, str] = {
    Estado.abierto: "Ticket creado y a la espera de un agente.",
    Estado.en_progreso: "Empezamos a trabajar en el ticket.",
    Estado.resuelto: "Aplicamos una solución; queda pendiente de confirmación.",
    Estado.cerrado: "Confirmada la solución. Cerramos el ticket.",
    Estado.reabierto: "El problema reapareció, reabrimos el ticket.",
}


async def seed() -> None:
    """
    Crea usuarios y tickets de ejemplo (idempotente).
    
    Idempotente significa que se puede ejecutar varias veces
    sin duplicar datos. Chequea si existen antes de crear.
    
    Proceso:
    1. Crear admin (si no existe)
    2. Crear usuarios de ejemplo (si no existen, chequeado por email)
    3. Crear 100 tickets (solo si la tabla está vacía)
    
    Nota: Los inserts de tickets usan SQLAlchemy Core (insert()),
    no ORM (session.add()), para evitar que disparen los listeners
    de events.py (que fijarían creado_en = now()).
    
    Parámetro:
        Ninguno (todo viene de config.py)
    """
    async with SessionLocal() as session:
        # ===== CREAR ADMIN =====
        # Buscar si ya existe
        admin = await session.scalar(
            select(User).where(User.email == settings.admin_email)
        )
        if admin is None:
            # No existe, crear
            admin = User(
                email=settings.admin_email,
                hashed_password=hash_password(settings.admin_password),
                nombre="Admin",
                apellidos="Deskly",
                is_admin=True,
            )
            session.add(admin)

        # ===== CREAR USUARIOS DE EJEMPLO =====
        for email, password, nombre, apellidos, is_admin in SAMPLE_USERS:
            # Buscar si el usuario ya existe
            existing_user = await session.scalar(
                select(User).where(User.email == email)
            )
            if existing_user is None:
                # No existe, crear
                session.add(
                    User(
                        email=email,
                        hashed_password=hash_password(password),
                        nombre=nombre,
                        apellidos=apellidos,
                        is_admin=is_admin,
                    )
                )

        # Guardar todos los usuarios
        await session.commit()

        # ===== CREAR TICKETS DE EJEMPLO =====
        # Solo si la tabla está vacía
        existing = await session.scalar(select(Ticket).limit(1))
        if existing is not None:
            # Ya hay tickets, salir
            return

        # Obtener todos los usuarios para mapearlos por ID
        users = (await session.scalars(select(User))).all()
        email_by_id = {u.id: u.email for u in users}
        user_ids = sorted(email_by_id)  # IDs de usuarios
        
        # Lista de posibles usuarios asignados (incluye None = sin asignar)
        assignees: list[int | None] = [*user_ids, None]

        # Listas para variar los tickets
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

        # RNG determinístico (mismo seed = mismo resultado cada ejecución)
        rng = random.Random(42)

        # Momento inicial: hace N días atrás
        base = datetime.now() - timedelta(days=len(asuntos))

        # ===== CREAR 100 TICKETS =====
        for i in range(100):
            # Variar estado, prioridad, asunto (mod para ciclar)
            estado = estados[i % len(estados)]
            prioridad = prioridades[i % len(prioridades)]
            asunto = asuntos[i % len(asuntos)]
            
            # Lógica de asignación:
            # - Si el ticket está "abierto": 50% asignado, 50% sin asignar
            # - Si está en otro estado: siempre asignar (un ticket en proceso debe tener responsable)
            if estado == Estado.abierto:
                asignado_id = rng.choice(user_ids) if (i % 2) == 0 else None
            else:
                asignado_id = rng.choice(user_ids)
            
            # El autor de los comentarios es el usuario asignado (o el sistema)
            autor = email_by_id.get(asignado_id, SYSTEM_AUTHOR)

            # Obtener el camino de ciclo de vida para este estado final
            path = LIFECYCLE_PATHS[estado]
            
            # Cada ticket comienza en tiempos diferentes (para no ser todos iguales)
            ticket_created = base + timedelta(minutes=i * len(estados))
            
            # El último cambio de estado ocurre en:
            # creación + número_de_transiciones * 1_minuto
            last_change_at = ticket_created + STEP * (len(path) - 1)

            # ===== INSERTAR TICKET CON INSERT() CORE =====
            # Usamos insert() en lugar de ORM add() para evitar
            # que disparen los listeners (queremos timestamps explícitos)
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

            # ===== CREAR HISTORIAL: UNA ENTRADA POR TRANSICIÓN =====
            # Para cada estado en el camino (ej: abierto -> en_progreso -> resuelto)
            # Crear:
            # 1. Un StateLog (auditoría)
            # 2. Un Comment (documento visible al usuario)
            for step_index, nuevo_estado in enumerate(path):
                # Timestamp de este cambio
                changed_at = ticket_created + STEP * step_index
                
                # Insertar StateLog
                await session.execute(
                    insert(StateLog),
                    {
                        "ticket_id": ticket_id,
                        "mensaje": f"Cambio de status: {nuevo_estado.value}",
                        "usuario_id": asignado_id,
                        "creado_en": changed_at,
                    },
                )
                
                # Insertar Comment
                await session.execute(
                    insert(Comment),
                    {
                        "ticket_id": ticket_id,
                        "autor": autor,
                        "cuerpo": STEP_COMMENTS[nuevo_estado],
                        "creado_en": changed_at,
                    },
                )

        # Guardar todos los tickets, comentarios e históricos
        await session.commit()
