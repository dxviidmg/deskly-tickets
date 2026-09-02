"""
MÓDULO: enums.py - Enumeraciones del dominio

Define constantes tipadas para valores que pueden tomar estados, prioridades y eventos.

En lugar de usar strings sueltos (ej: estado = "abierto"), usamos enums:
- Evita typos: el IDE autocomplete sugerirá Estado.abierto
- Type-safe: el lenguaje verifica que solo uses valores válidos
- Documentado: cada enum tiene nombres legibles

Nota: todas las enums heredan de str para que se serialicen bien a JSON
(cuando FastAPI convierte la respuesta a JSON, puede convertir enum a string).
"""

from enum import Enum, StrEnum


class Estado(str, Enum):
    """
    Estados posibles de un ticket en su ciclo de vida.
    
    El flujo es: abierto → en_progreso → resuelto → cerrado
    Con la posibilidad de reabierto si vuelve a haber problemas.
    
    Valores:
    - abierto: Ticket creado, esperando que alguien lo atienda
    - en_progreso: Un agente está trabajando en él
    - resuelto: Se propone una solución, pero queda pendiente de confirmación del cliente
    - reabierto: El cliente confirmó que el problema reapareció
    - cerrado: Solución confirmada, ticket finalizado
    """

    abierto = "abierto"
    en_progreso = "en_progreso"
    resuelto = "resuelto"
    reabierto = "reabierto"
    cerrado = "cerrado"


class Prioridad(str, Enum):
    """
    Niveles de prioridad de un ticket.
    
    Se usan para:
    - Ordenar el trabajo: qué tickets resolver primero
    - Filtrar: mostrar solo tickets urgentes en el listado
    - SLA: tickets urgentes tienen deadline más corto
    
    Valores (de menor a mayor):
    - baja: No es urgente, se puede atender en días
    - media: Prioridad normal, se atiende en orden
    - alta: Se debería resolver pronto (horas)
    - urgente: Impacto crítico, resolver inmediatamente
    """

    baja = "baja"
    media = "media"
    alta = "alta"
    urgente = "urgente"


class DomainEvent(StrEnum):
    """
    Tipos de eventos que se envían a través de WebSocket.
    
    Cada evento representa un cambio importante que todos los clientes
    conectados deberían conocer. Se transmiten vía Redis pub/sub.
    
    Eventos:
    - TICKET_CREATED: Se creó un nuevo ticket
    - TICKET_UPDATED: Un ticket fue modificado (estado, asignado, etc.)
    - TICKET_COMMENTED: Se agregó un comentario a un ticket
    
    Ejemplo de uso en el código:
        await manager.broadcast(DomainEvent.TICKET_CREATED, ticket_data)
    
    El cliente WebSocket recibe esto como:
        {
            "tipo": "ticket.creado",
            "datos": {...ticket...}
        }
    """

    TICKET_CREATED = "ticket.creado"
    TICKET_UPDATED = "ticket.actualizado"
    TICKET_COMMENTED = "ticket.comentado"
