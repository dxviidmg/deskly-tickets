"""SQLAlchemy listeners for state_log and WebSocket event broadcasting."""
from datetime import datetime

from sqlalchemy import event, insert
from sqlalchemy.orm import object_session
from sqlalchemy.orm.attributes import get_history

from app.enums import DomainEvent
from app.models import StateLog, Ticket, User

# Re-export for backward compatibility (routers import from here)
TICKET_CREATED = DomainEvent.TICKET_CREATED
TICKET_UPDATED = DomainEvent.TICKET_UPDATED
TICKET_COMMENTED = DomainEvent.TICKET_COMMENTED


@event.listens_for(Ticket, "after_insert", propagate=True)
def receive_ticket_after_insert(mapper, connection, target: Ticket):
    """Log initial ticket creation."""
    stmt = insert(StateLog).values(
        ticket_id=target.id,
        mensaje=f"Cambio de status: {target.estado}",
        usuario_id=None,
        creado_en=datetime.now(),
    )
    connection.execute(stmt)


@event.listens_for(Ticket, "after_update", propagate=True)
def receive_ticket_after_update(mapper, connection, target: Ticket):
    """Log ticket estado and asignado_a_id changes."""
    session = object_session(target)
    if session is None:
        return

    # Detect changes using SQLAlchemy history
    estado_history = get_history(target, "estado")
    asignado_history = get_history(target, "asignado_a_id")

    # Log estado change
    if estado_history.has_changes() and estado_history.modified:
        nuevo_estado = estado_history.added[0] if estado_history.added else target.estado
        stmt = insert(StateLog).values(
            ticket_id=target.id,
            mensaje=f"Cambio de status: {nuevo_estado}",
            usuario_id=None,
            creado_en=datetime.now(),
        )
        connection.execute(stmt)

    # Log asignado_a_id change
    if asignado_history.has_changes():
        nuevo_id = target.asignado_a_id
        if nuevo_id is None:
            mensaje = "Asignado a: Sin asignar"
        else:
            # Try to get the user email from the session
            # This is a best-effort approach; if not available, use the ID
            user = session.query(User).filter(User.id == nuevo_id).first()
            mensaje = f"Asignado a: {user.email}" if user else f"Asignado a: usuario {nuevo_id}"

        stmt = insert(StateLog).values(
            ticket_id=target.id,
            mensaje=mensaje,
            usuario_id=nuevo_id,
            creado_en=datetime.now(),
        )
        connection.execute(stmt)
