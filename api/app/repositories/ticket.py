"""Repository for Ticket entity.

Encapsulates database operations and business logic, keeping routers thin.
"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.enums import Estado, Prioridad
from app.models import Comment, Ticket, User
from app.schemas import CommentCreate, Page, TicketCreate, TicketDetail, TicketOut, TicketUpdate
from app.state_machine import assert_transition


class TicketRepository:
    """Handles all Ticket-related database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_404(self, ticket_id: int) -> Ticket:
        """Get a ticket by ID or raise HTTPException(404)."""
        from fastapi import HTTPException, status

        ticket = await self.session.get(Ticket, ticket_id)
        if ticket is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado"
            )
        return ticket

    async def get_with_details(self, ticket_id: int) -> Ticket:
        """Get a ticket with comments and state_log loaded."""
        from fastapi import HTTPException, status

        stmt = (
            select(Ticket)
            .where(Ticket.id == ticket_id)
            .options(selectinload(Ticket.comments), selectinload(Ticket.state_log))
        )
        ticket = await self.session.scalar(stmt)
        if ticket is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado"
            )
        return ticket

    async def list_with_filters(
        self,
        page: int = 1,
        size: int = 20,
        estado: Estado | None = None,
        prioridad: Prioridad | None = None,
        asignado_a_id: int | None = None,
    ) -> Page[TicketOut]:
        """List tickets with optional filters and pagination."""
        filters = []
        if estado is not None:
            filters.append(Ticket.estado == estado)
        if prioridad is not None:
            filters.append(Ticket.prioridad == prioridad)
        if asignado_a_id is not None:
            if asignado_a_id == -1:
                filters.append(Ticket.asignado_a_id.is_(None))
            else:
                filters.append(Ticket.asignado_a_id == asignado_a_id)

        total_stmt = select(func.count()).select_from(Ticket)
        if filters:
            total_stmt = total_stmt.where(*filters)
        total = await self.session.scalar(total_stmt) or 0

        stmt = (
            select(Ticket)
            .where(*filters)
            .order_by(Ticket.creado_en.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.session.scalars(stmt)
        items = [TicketOut.model_validate(t) for t in result.all()]
        return Page[TicketOut](items=items, total=total, page=page, size=size)

    async def validate_assignee(self, user_id: int | None) -> None:
        """Validate that a user exists, raise HTTPException(422) if not."""
        from fastapi import HTTPException, status

        if user_id is None:
            return
        if await self.session.get(User, user_id) is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El usuario asignado no existe",
            )

    async def create(self, payload: TicketCreate) -> Ticket:
        """Create a new ticket."""
        await self.validate_assignee(payload.asignado_a_id)
        ticket = Ticket(**payload.model_dump())
        self.session.add(ticket)
        await self.session.commit()
        await self.session.refresh(ticket)
        return ticket

    async def update(self, ticket_id: int, payload: TicketUpdate) -> Ticket:
        """Partially update a ticket."""
        ticket = await self.get_or_404(ticket_id)
        data = payload.model_dump(exclude_unset=True)
        if "asignado_a_id" in data:
            await self.validate_assignee(data["asignado_a_id"])
        for field, value in data.items():
            setattr(ticket, field, value)
        await self.session.commit()
        await self.session.refresh(ticket)
        return ticket

    async def transition(self, ticket_id: int, nuevo_estado: Estado) -> Ticket:
        """Transition ticket to a new state."""
        ticket = await self.get_or_404(ticket_id)
        assert_transition(ticket.estado, nuevo_estado)
        ticket.estado = nuevo_estado
        await self.session.commit()
        await self.session.refresh(ticket)
        return ticket

    async def add_comment(self, ticket_id: int, autor: str, payload: CommentCreate) -> Comment:
        """Add a comment to a ticket."""
        ticket = await self.get_or_404(ticket_id)
        comment = Comment(ticket_id=ticket.id, autor=autor, cuerpo=payload.cuerpo)
        self.session.add(comment)
        await self.session.commit()
        await self.session.refresh(comment)
        return comment

    async def to_out(self, ticket: Ticket) -> TicketOut:
        """Convert a Ticket model to TicketOut schema."""
        await self.session.refresh(ticket, attribute_names=["asignado"])
        return TicketOut.model_validate(ticket)
