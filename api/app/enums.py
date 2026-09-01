"""Domain enumerations for tickets."""
from enum import Enum, StrEnum


class Estado(str, Enum):
    """Ticket lifecycle states."""

    abierto = "abierto"
    en_progreso = "en_progreso"
    resuelto = "resuelto"
    reabierto = "reabierto"
    cerrado = "cerrado"


class Prioridad(str, Enum):
    """Ticket priority levels."""

    baja = "baja"
    media = "media"
    alta = "alta"
    urgente = "urgente"


class DomainEvent(StrEnum):
    """WebSocket event types broadcast via Redis pub/sub."""

    TICKET_CREATED = "ticket.creado"
    TICKET_UPDATED = "ticket.actualizado"
    TICKET_COMMENTED = "ticket.comentado"
