"""
MÓDULO: events.py - Listeners de SQLAlchemy para auditoría

Los "listeners" son funciones que se ejecutan automáticamente cuando
algo ocurre en la BD (insert, update, delete).

En Deskly, usamos listeners para:
- Crear registros de auditoría (state_log) automáticamente
- No duplicar lógica en cada router

¿Cómo funciona?
1. Router: await repo.transition(ticket_id, Estado.en_progreso)
2. Repo actualiza el modelo y hace session.commit()
3. SQLAlchemy detecta que cambió el campo "estado"
4. SQLAlchemy dispara receive_ticket_after_update()
5. receive_ticket_after_update() crea un StateLog automáticamente

Ventajas:
- Centralizador: la lógica de auditoría está aquí
- Automático: no importa cómo se modifique el ticket (router, script, etc.)
- Consistente: siempre se crea el log, sin excepciones

Listeners disponibles:
- after_insert: después de insertar una fila
- after_update: después de actualizar una fila
- before_delete: antes de borrar una fila
- ... y muchos más
"""

from datetime import datetime

from sqlalchemy import event, insert
from sqlalchemy.orm import object_session
from sqlalchemy.orm.attributes import get_history

from app.enums import DomainEvent
from app.models import StateLog, Ticket, User

# Re-exportar constantes de eventos para que los routers las importen desde aquí
TICKET_CREATED = DomainEvent.TICKET_CREATED
TICKET_UPDATED = DomainEvent.TICKET_UPDATED
TICKET_COMMENTED = DomainEvent.TICKET_COMMENTED


@event.listens_for(Ticket, "after_insert", propagate=True)
def receive_ticket_after_insert(mapper, connection, target: Ticket):
    """
    Listener: se ejecuta automáticamente después de crear un ticket.
    
    Crea un registro de auditoría (StateLog) con el estado inicial del ticket.
    
    Parámetros (los proporciona SQLAlchemy automáticamente):
    - mapper: Metadatos de la clase Ticket
    - connection: Conexión a la BD (se usa para ejecutar SQL)
    - target: La instancia de Ticket que se acaba de insertar
    
    Qué hace:
    - Extrae el estado inicial del ticket (siempre "abierto")
    - Inserta un StateLog con mensaje "Cambio de status: abierto"
    
    IMPORTANTE: aquí usamos connection.execute() directamente (SQL Core)
    porque el listener se ejecuta al finalizar la transacción (después del commit).
    No podemos usar session.add() porque la sesión ya se cerró.
    """
    # Crear un registro de auditoría con el estado inicial
    stmt = insert(StateLog).values(
        ticket_id=target.id,
        mensaje=f"Cambio de status: {target.estado}",  # Por defecto "abierto"
        usuario_id=None,  # El sistema hizo el cambio, no un usuario
        creado_en=datetime.now(),
    )
    connection.execute(stmt)


@event.listens_for(Ticket, "after_update", propagate=True)
def receive_ticket_after_update(mapper, connection, target: Ticket):
    """
    Listener: se ejecuta automáticamente después de actualizar un ticket.
    
    Detecta cambios en:
    - estado: si cambió de estado, crea un StateLog
    - asignado_a_id: si cambió la asignación, crea un StateLog
    
    Parámetros (iguales que receive_ticket_after_insert).
    
    ¿Cómo detectar cambios?
    - get_history(target, "campo"): devuelve (added, unchanged, deleted)
    - Chequeamos si has_changes() para saber si cambió
    
    Ejemplo:
    - Antes: estado = "abierto", asignado_a_id = 1
    - Actualización: await repo.transition(5, Estado.en_progreso)
    - Ahora: estado = "en_progreso", asignado_a_id = 1
    - Listener crea StateLog: "Cambio de status: en_progreso"
    """
    # Obtener la sesión (la usaremos para queries)
    session = object_session(target)
    if session is None:
        return

    # ===== DETECTAR CAMBIO DE ESTADO =====
    # get_history devuelve información de qué cambió en el campo "estado"
    estado_history = get_history(target, "estado")
    
    # Verificar si el campo "estado" tiene cambios.
    # has_changes() ya indica si el valor fue modificado; el objeto History de
    # SQLAlchemy NO tiene atributo `.modified` (solo added/deleted/unchanged),
    # así que basta con has_changes().
    if estado_history.has_changes():
        # El nuevo estado es el último valor en "added"
        nuevo_estado = estado_history.added[0] if estado_history.added else target.estado
        
        # Crear un StateLog
        stmt = insert(StateLog).values(
            ticket_id=target.id,
            mensaje=f"Cambio de status: {nuevo_estado}",
            usuario_id=None,
            creado_en=datetime.now(),
        )
        connection.execute(stmt)

    # ===== DETECTAR CAMBIO DE ASIGNADO =====
    # Igual que estado, pero para asignado_a_id
    asignado_history = get_history(target, "asignado_a_id")
    
    if asignado_history.has_changes():
        nuevo_id = target.asignado_a_id
        
        # Construir mensaje según si se asignó o se desasignó
        if nuevo_id is None:
            mensaje = "Asignado a: Sin asignar"
        else:
            # Intentar obtener el email del usuario desde la sesión
            # (best-effort: si no está cargado, usamos solo el ID)
            user = session.query(User).filter(User.id == nuevo_id).first()
            mensaje = f"Asignado a: {user.email}" if user else f"Asignado a: usuario {nuevo_id}"

        # Crear un StateLog
        stmt = insert(StateLog).values(
            ticket_id=target.id,
            mensaje=mensaje,
            usuario_id=nuevo_id,
            creado_en=datetime.now(),
        )
        connection.execute(stmt)
