"""Máquina de estados explícita para tickets.

Define qué transiciones de estado son válidas. Cualquier transición
que no esté en el mapa se rechaza con InvalidTransitionError.

Esto permite que la lógica de negocio esté centralizada y sea testeable.
"""
from app.enums import Estado

# Mapa de transiciones: estado -> conjunto de estados alcanzables
ALLOWED_TRANSITIONS: dict[Estado, set[Estado]] = {
    Estado.abierto: {Estado.en_progreso},
    Estado.en_progreso: {Estado.resuelto},
    # Desde "resuelto" se puede cerrar o reabrir
    Estado.resuelto: {Estado.cerrado, Estado.abierto},
    Estado.cerrado: set(),  # Estado final, sin transiciones
}


class InvalidTransitionError(Exception):
    """Excepción lanzada cuando una transición de estado no es válida.
    
    Contiene información sobre el estado actual, el solicitado y
    los estados permitidos desde el actual.
    """

    def __init__(self, current: Estado, requested: Estado) -> None:
        # Normalizar a enum (pueden venir strings de la DB)
        current = Estado(current)
        requested = Estado(requested)
        self.current = current
        self.requested = requested
        # Lista de estados permitidos desde el actual
        self.allowed = sorted(
            e.value for e in ALLOWED_TRANSITIONS.get(current, set())
        )
        super().__init__(
            f"Invalid transition {current.value} -> {requested.value}"
        )


def can_transition(current: Estado, requested: Estado) -> bool:
    """Devuelve True si la transición de current a requested es válida.
    
    Acepta tanto valores del enum Estado como strings (útil cuando
    el estado viene de la base de datos como texto).
    
    Args:
        current: Estado actual del ticket
        requested: Estado al que se quiere transicionar
        
    Returns:
        True si la transición es válida, False en caso contrario
    """
    current = Estado(current)
    requested = Estado(requested)
    return requested in ALLOWED_TRANSITIONS.get(current, set())


def assert_transition(current: Estado, requested: Estado) -> None:
    """Lanza InvalidTransitionError si la transición no es válida.
    
    Útil para usar en el código: si la transición es inválida, se
    lanza excepción que el router convierte en HTTP 409.
    
    Args:
        current: Estado actual del ticket
        requested: Estado al que se quiere transicionar
        
    Raises:
        InvalidTransitionError: Si la transición no está permitida
    """
    if not can_transition(current, requested):
        raise InvalidTransitionError(current, requested)
