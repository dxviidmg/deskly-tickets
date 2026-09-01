"""Enumeraciones del dominio.

Define los valores posibles para estados, prioridades y tipos de eventos
que se usan en todo el sistema. Al ser enums, se garantiza type-safety
y se evitan typos.
"""
from enum import Enum, StrEnum


class Estado(str, Enum):
    """Estados del ciclo de vida de un ticket.
    
    El flujo es: abierto → en_progreso → resuelto → cerrado
    Con posibilidad de reabrir desde resuelto.
    """

    abierto = "abierto"
    en_progreso = "en_progreso"
    resuelto = "resuelto"
    reabierto = "reabierto"
    cerrado = "cerrado"


class Prioridad(str, Enum):
    """Niveles de prioridad de un ticket.
    
    Se usan para filtrar y ordenar tickets en el dashboard.
    """

    baja = "baja"
    media = "media"
    alta = "alta"
    urgente = "urgente"


class DomainEvent(StrEnum):
    """Tipos de eventos WebSocket que se difunden via Redis pub/sub.
    
    Estos eventos se envían a todos los clientes conectados cuando
    ocurre un cambio en el sistema (creación, actualización, comentario).
    """

    TICKET_CREATED = "ticket.creado"
    TICKET_UPDATED = "ticket.actualizado"
    TICKET_COMMENTED = "ticket.comentado"
