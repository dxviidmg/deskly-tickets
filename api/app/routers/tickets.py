"""
MÓDULO: routers/tickets.py - CRUD de tickets y cambios de estado

Define endpoints para gestionar tickets: crear, listar, actualizar, cambiar estado,
añadir comentarios.

Endpoints:
- POST /api/tickets: Crear ticket
- GET /api/tickets: Listar tickets (con filtros y paginación)
- GET /api/tickets/{id}: Obtener ticket con detalles
- PATCH /api/tickets/{id}: Actualizar ticket
- POST /api/tickets/{id}/transicion: Cambiar estado
- POST /api/tickets/{id}/comentarios: Añadir comentario

IMPORTANTE:
- Todos requieren autenticación (no admin)
- Cambio de estado se hace en endpoint separado (/transicion)
- Se publica evento WebSocket después de cada cambio
"""

from fastapi import APIRouter, Depends, Query

from app.db import get_session
from app.deps import get_current_user
from app.enums import DomainEvent, Estado, Prioridad
from app.models import User
from app.repositories.ticket import TicketRepository
from app.schemas import (
    CommentCreate,
    CommentOut,
    Page,
    TicketCreate,
    TicketDetail,
    TicketOut,
    TicketUpdate,
    TransitionIn,
)
from app.ws import manager

router = APIRouter(
    prefix="/api/tickets",
    tags=["tickets"],
    dependencies=[Depends(get_current_user)],  # Requiere autenticación
)


def get_repo(session=Depends(get_session)) -> TicketRepository:
    """
    Dependencia que proporciona un TicketRepository.
    
    El repository encapsula la lógica de acceso a BD para tickets.
    Permite que los routers sean delgados y testables.
    
    Args:
        session: Sesión de BD (inyectada)
        
    Returns:
        TicketRepository para usar en el handler
    """
    return TicketRepository(session)


@router.post("", response_model=TicketOut, status_code=201)
async def create_ticket(
    payload: TicketCreate,
    repo: TicketRepository = Depends(get_repo)
) -> TicketOut:
    """
    Crea un nuevo ticket.
    
    Require: Autenticación
    
    Args:
        payload (TicketCreate): { titulo, descripcion, prioridad, asignado_a_id }
        repo (TicketRepository): Repository para acceso a BD
        
    Returns:
        TicketOut: Ticket creado
        
    Raises:
        422: Si el usuario asignado no existe
        
    Proceso:
    1. Validar que el usuario asignado existe (si se especifica)
    2. Crear ticket en BD
    3. Publicar evento WebSocket para que otros clientes lo vean
    4. Devolver ticket
    """
    ticket = await repo.create(payload)
    out = await repo.to_out(ticket)
    await manager.broadcast(DomainEvent.TICKET_CREATED, out)
    return out


@router.get("", response_model=Page[TicketOut])
async def list_tickets(
    repo: TicketRepository = Depends(get_repo),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    estado: Estado | None = None,
    prioridad: Prioridad | None = None,
    asignado_a_id: int | None = None,
) -> Page[TicketOut]:
    """
    Lista tickets con filtros y paginación.
    
    Require: Autenticación
    
    Query params:
    - page: Número de página (por defecto 1)
    - size: Items por página (por defecto 20, máximo 100)
    - estado: Filtrar por estado (ej: ?estado=abierto)
    - prioridad: Filtrar por prioridad (ej: ?prioridad=alta)
    - asignado_a_id: Filtrar por usuario asignado (ej: ?asignado_a_id=5)
                      Usar -1 para "sin asignar" (NULL)
    
    Returns:
        Page[TicketOut]: Página con items, total, número y tamaño
        
    Ejemplo:
        GET /api/tickets?page=1&size=20&estado=abierto&prioridad=alta
    """
    return await repo.list_with_filters(
        page=page,
        size=size,
        estado=estado,
        prioridad=prioridad,
        asignado_a_id=asignado_a_id,
    )


@router.get("/{ticket_id}", response_model=TicketDetail)
async def get_ticket(
    ticket_id: int,
    repo: TicketRepository = Depends(get_repo)
) -> TicketDetail:
    """
    Obtiene un ticket con todos sus detalles.
    
    Require: Autenticación
    
    Detalles incluyen:
    - Ticket: id, titulo, descripción, estado, prioridad, etc.
    - Comentarios: lista de comentarios del ticket
    - State log: historial de cambios de estado
    
    Args:
        ticket_id: ID del ticket
        repo: Repository para acceso a BD
        
    Returns:
        TicketDetail: Ticket con comentarios e historial
        
    Raises:
        404: Si el ticket no existe
    """
    return await repo.get_with_details(ticket_id)


@router.patch("/{ticket_id}", response_model=TicketOut)
async def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    repo: TicketRepository = Depends(get_repo),
) -> TicketOut:
    """
    Actualiza parcialmente un ticket.
    
    Require: Autenticación
    
    IMPORTANTE: para cambiar el estado, usar /transicion, NO este endpoint.
    
    Args:
        ticket_id: ID del ticket
        payload (TicketUpdate): Campos a actualizar (todos opcionales)
        repo: Repository para acceso a BD
        
    Returns:
        TicketOut: Ticket actualizado
        
    Raises:
        404: Si no existe
        422: Si el usuario asignado no existe
        
    Ejemplo:
        PATCH /api/tickets/5
        { "titulo": "Nuevo título" }
    """
    ticket = await repo.update(ticket_id, payload)
    out = await repo.to_out(ticket)
    await manager.broadcast(DomainEvent.TICKET_UPDATED, out)
    return out


@router.post("/{ticket_id}/transicion", response_model=TicketOut)
async def transition_ticket(
    ticket_id: int,
    payload: TransitionIn,
    repo: TicketRepository = Depends(get_repo),
) -> TicketOut:
    """
    Cambia el estado de un ticket.
    
    Require: Autenticación
    
    IMPORTANTE: solo este endpoint puede cambiar estado,
    para garantizar que la máquina de estados se respeta.
    
    Args:
        ticket_id: ID del ticket
        payload (TransitionIn): { nuevo_estado: Estado }
        repo: Repository para acceso a BD
        
    Returns:
        TicketOut: Ticket con nuevo estado
        
    Raises:
        404: Si el ticket no existe
        409: Si la transición no es válida (máquina de estados)
        
    Ejemplo:
        POST /api/tickets/5/transicion
        { "nuevo_estado": "en_progreso" }
    """
    ticket = await repo.transition(ticket_id, payload.nuevo_estado)
    out = await repo.to_out(ticket)
    await manager.broadcast(DomainEvent.TICKET_UPDATED, out)
    return out


@router.post(
    "/{ticket_id}/comentarios",
    response_model=CommentOut,
    status_code=201,
)
async def add_comment(
    ticket_id: int,
    payload: CommentCreate,
    repo: TicketRepository = Depends(get_repo),
    current: User = Depends(get_current_user),
) -> CommentOut:
    """
    Añade un comentario a un ticket.
    
    Require: Autenticación
    
    El autor del comentario es automáticamente el usuario autenticado
    (se toma su email).
    
    Args:
        ticket_id: ID del ticket
        payload (CommentCreate): { cuerpo: str }
        repo: Repository para acceso a BD
        current: Usuario autenticado (inyectado)
        
    Returns:
        CommentOut: Comentario creado
        
    Raises:
        404: Si el ticket no existe
        
    Ejemplo:
        POST /api/tickets/5/comentarios
        { "cuerpo": "Ya he resuelto el problema" }
    """
    comment = await repo.add_comment(ticket_id, current.email, payload)
    ticket = await repo.get_or_404(ticket_id)
    out = await repo.to_out(ticket)
    await manager.broadcast(DomainEvent.TICKET_COMMENTED, out)
    return comment
