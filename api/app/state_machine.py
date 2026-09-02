"""
MÓDULO: state_machine.py - Máquina de estados explícita

Una máquina de estados define qué transiciones son válidas.

En Deskly, un ticket NO puede:
- Ir de "resuelto" a "en_progreso" directamente
- Ir de "cerrado" a otro estado
- Saltarse estados

Con una máquina de estados explícita:
- La lógica de negocio está centralizada
- Es fácil testear (sin tocar la BD)
- Los errores son claros (409 Conflict en lugar de 500 Internal Error)
- Es fácil cambiar reglas después (modificar ALLOWED_TRANSITIONS)

Diagrama de estados:
    abierto
      |
      v
    en_progreso <----+
      |              |
      v              |
    resuelto         |
      |   \          |
      |    v         |
      |  reabierto --+
      v    |
    cerrado <--------+

Transiciones válidas:
- abierto → en_progreso
- en_progreso → resuelto
- resuelto → cerrado
- resuelto → reabierto (el problema reapareció)
- reabierto → en_progreso (se retoma el trabajo)
- reabierto → cerrado
- cerrado → (ninguno, estado terminal)
"""

from app.enums import Estado

# Mapa de transiciones: estado → conjunto de estados alcanzables desde él
ALLOWED_TRANSITIONS: dict[Estado, set[Estado]] = {
    Estado.abierto: {Estado.en_progreso},
    Estado.en_progreso: {Estado.resuelto},
    # Desde "resuelto": se cierra (confirmado) o se reabre (el problema volvió).
    Estado.resuelto: {Estado.cerrado, Estado.reabierto},
    # Desde "reabierto": se retoma el trabajo o se cierra directamente.
    Estado.reabierto: {Estado.en_progreso, Estado.cerrado},
    # Desde "cerrado" no hay transiciones (estado final)
    Estado.cerrado: set(),
}


class InvalidTransitionError(Exception):
    """
    Excepción lanzada cuando se intenta una transición inválida.
    
    Ejemplo: usuario intenta cambiar ticket de "cerrado" a "en_progreso"
    
    Attributes:
        current (Estado): Estado actual del ticket
        requested (Estado): Estado al que se quiso cambiar
        allowed (list[str]): Estados válidos desde el actual
    """

    def __init__(self, current: Estado, requested: Estado) -> None:
        """
        Inicializa la excepción con información de la transición fallida.
        
        Args:
            current: Estado actual (puede ser string o enum)
            requested: Estado solicitado (puede ser string o enum)
        """
        # Normalizar a enum (por si vienen como strings de la BD)
        current = Estado(current)
        requested = Estado(requested)

        self.current = current
        self.requested = requested

        # Lista de estados permitidos desde el actual (ordenados)
        self.allowed = sorted(
            e.value for e in ALLOWED_TRANSITIONS.get(current, set())
        )

        # Mensaje de error
        super().__init__(
            f"Invalid transition {current.value} -> {requested.value}"
        )


def can_transition(current: Estado, requested: Estado) -> bool:
    """
    Devuelve True si una transición es válida.
    
    Args:
        current (Estado): Estado actual del ticket
        requested (Estado): Estado al que se quiere ir
        
    Returns:
        bool: True si la transición está en ALLOWED_TRANSITIONS, False si no
        
    Ejemplo:
        if can_transition(Estado.abierto, Estado.en_progreso):
            print("Transición válida")
        else:
            print("Transición inválida")
    """
    # Normalizar a enum (pueden ser strings de la BD)
    current = Estado(current)
    requested = Estado(requested)

    # Buscar current en el mapa, si no existe devolver set() vacío
    allowed_from_current = ALLOWED_TRANSITIONS.get(current, set())

    # Verificar si requested está en los permitidos
    return requested in allowed_from_current


def assert_transition(current: Estado, requested: Estado) -> None:
    """
    Lanza InvalidTransitionError si la transición NO es válida.
    
    Se usa en los routers: si la transición falla, esta función lanza
    excepción que FastAPI convierte en HTTP 409.
    
    Args:
        current (Estado): Estado actual del ticket
        requested (Estado): Estado al que se quiere ir
        
    Raises:
        InvalidTransitionError: Si la transición no está permitida
        
    Ejemplo:
        @router.post("/tickets/{id}/transicion")
        async def transition(ticket_id: int, payload: TransitionIn):
            ticket = await repo.get_or_404(ticket_id)
            assert_transition(ticket.estado, payload.nuevo_estado)  # Lanza si es inválida
            ticket.estado = payload.nuevo_estado
            await session.commit()
    """
    if not can_transition(current, requested):
        raise InvalidTransitionError(current, requested)
