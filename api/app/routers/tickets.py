"""Ticket REST endpoints: CRUD, state transition and comments.

All endpoints require an authenticated user. Assignment references a user id;
comment authors are taken from the authenticated user.
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
    dependencies=[Depends(get_current_user)],
)


def get_repo(session=Depends(get_session)) -> TicketRepository:
    """Dependency that provides a TicketRepository."""
    return TicketRepository(session)


@router.post("", response_model=TicketOut, status_code=201)
async def create_ticket(
    payload: TicketCreate, repo: TicketRepository = Depends(get_repo)
) -> TicketOut:
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
    return await repo.list_with_filters(
        page=page,
        size=size,
        estado=estado,
        prioridad=prioridad,
        asignado_a_id=asignado_a_id,
    )


@router.get("/{ticket_id}", response_model=TicketDetail)
async def get_ticket(
    ticket_id: int, repo: TicketRepository = Depends(get_repo)
) -> TicketDetail:
    return await repo.get_with_details(ticket_id)


@router.patch("/{ticket_id}", response_model=TicketOut)
async def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    repo: TicketRepository = Depends(get_repo),
) -> TicketOut:
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
    comment = await repo.add_comment(ticket_id, current.email, payload)
    ticket = await repo.get_or_404(ticket_id)
    out = await repo.to_out(ticket)
    await manager.broadcast(DomainEvent.TICKET_COMMENTED, out)
    return comment
