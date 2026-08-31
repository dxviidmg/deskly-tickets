"""Domain enumerations for tickets."""
from enum import Enum


class Estado(str, Enum):
    """Ticket lifecycle states."""

    abierto = "abierto"
    en_progreso = "en_progreso"
    resuelto = "resuelto"
    cerrado = "cerrado"


class Prioridad(str, Enum):
    """Ticket priority levels."""

    baja = "baja"
    media = "media"
    alta = "alta"
    urgente = "urgente"
