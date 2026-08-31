"""Ticket REST endpoints: CRUD, state transition and comments."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.enums import Estado, Prioridad
from app.events import TICKET_COMMENTED, TICKET_CREATED, TICKET_UPDATED
from app.models import Comment, Ticket
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
from app.state_machine import assert_transition
from app.ws import manager

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


async def _get_ticket_or_404(session: AsyncSession, ticket_id: uuid.UUID) -> Ticket:
    ticket = await session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado"
        )
    return ticket


@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: TicketCreate, session: AsyncSession = Depends(get_session)
) -> Ticket:
    ticket = Ticket(**payload.model_dump())
    session.add(ticket)
    await session.commit()
    await session.refresh(ticket)
    await manager.broadcast(TICKET_CREATED, TicketOut.model_validate(ticket))
    return ticket


@router.get("", response_model=Page[TicketOut])
async def list_tickets(
    session: AsyncSession = Depends(get_session),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    estado: Estado | None = None,
    prioridad: Prioridad | None = None,
) -> Page[TicketOut]:
    filters = []
    if estado is not None:
        filters.append(Ticket.estado == estado)
    if prioridad is not None:
        filters.append(Ticket.prioridad == prioridad)

    total_stmt = select(func.count()).select_from(Ticket)
    if filters:
        total_stmt = total_stmt.where(*filters)
    total = await session.scalar(total_stmt) or 0

    stmt = (
        select(Ticket)
        .where(*filters)
        .order_by(Ticket.creado_en.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await session.scalars(stmt)
    items = [TicketOut.model_validate(t) for t in result.all()]
    return Page[TicketOut](items=items, total=total, page=page, size=size)


@router.get("/{ticket_id}", response_model=TicketDetail)
async def get_ticket(
    ticket_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Ticket:
    stmt = (
        select(Ticket)
        .where(Ticket.id == ticket_id)
        .options(selectinload(Ticket.comments))
    )
    ticket = await session.scalar(stmt)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado"
        )
    return ticket


@router.patch("/{ticket_id}", response_model=TicketOut)
async def update_ticket(
    ticket_id: uuid.UUID,
    payload: TicketUpdate,
    session: AsyncSession = Depends(get_session),
) -> Ticket:
    ticket = await _get_ticket_or_404(session, ticket_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(ticket, field, value)
    await session.commit()
    await session.refresh(ticket)
    await manager.broadcast(TICKET_UPDATED, TicketOut.model_validate(ticket))
    return ticket


@router.post("/{ticket_id}/transicion", response_model=TicketOut)
async def transition_ticket(
    ticket_id: uuid.UUID,
    payload: TransitionIn,
    session: AsyncSession = Depends(get_session),
) -> Ticket:
    ticket = await _get_ticket_or_404(session, ticket_id)
    # Raises InvalidTransitionError -> mapped to HTTP 409 by exception handler.
    assert_transition(ticket.estado, payload.nuevo_estado)
    ticket.estado = payload.nuevo_estado
    await session.commit()
    await session.refresh(ticket)
    await manager.broadcast(TICKET_UPDATED, TicketOut.model_validate(ticket))
    return ticket


@router.post(
    "/{ticket_id}/comentarios",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_comment(
    ticket_id: uuid.UUID,
    payload: CommentCreate,
    session: AsyncSession = Depends(get_session),
) -> Comment:
    ticket = await _get_ticket_or_404(session, ticket_id)
    comment = Comment(ticket_id=ticket.id, **payload.model_dump())
    session.add(comment)
    await session.commit()
    await session.refresh(comment)
    # Refresh ticket so subscribers get the updated ticket alongside the event.
    await session.refresh(ticket)
    await manager.broadcast(TICKET_COMMENTED, TicketOut.model_validate(ticket))
    return comment
