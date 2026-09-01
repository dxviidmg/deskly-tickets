"""Repositorio para la entidad Ticket.

Encapsula todas las operaciones de base de datos relacionadas con tickets,
manteniendo los routers delgados y la lógica de negocio testeable.

Patrón Repository: separa la lógica de acceso a datos de la lógica de
presentación (routers) y de negocio (state_machine, events).
"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.enums import Estado, Prioridad
from app.models import Comment, Ticket, User
from app.schemas import CommentCreate, Page, TicketCreate, TicketDetail, TicketOut, TicketUpdate
from app.state_machine import assert_transition


class TicketRepository:
    """Maneja todas las operaciones de base de datos relacionadas con tickets.
    
    Métodos principales:
    - get_or_404: Obtener un ticket por ID
    - get_with_details: Obtener con comentarios e historial
    - list_with_filters: Listar con filtros y paginación
    - create: Crear un nuevo ticket
    - update: Actualizar parcialmente un ticket
    - transition: Cambiar el estado de un ticket
    - add_comment: Añadir un comentario
    """

    def __init__(self, session: AsyncSession):
        """Inicializa el repositorio con una sesión de base de datos.
        
        Args:
            session: Sesión asíncrona de SQLAlchemy
        """
        self.session = session

    async def get_or_404(self, ticket_id: int) -> Ticket:
        """Obtiene un ticket por ID o lanza HTTPException(404).
        
        Args:
            ticket_id: ID del ticket
            
        Returns:
            El ticket encontrado
            
        Raises:
            HTTPException: Si el ticket no existe
        """
        from fastapi import HTTPException, status

        ticket = await self.session.get(Ticket, ticket_id)
        if ticket is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado"
            )
        return ticket

    async def get_with_details(self, ticket_id: int) -> Ticket:
        """Obtiene un ticket con comentarios e historial cargados.
        
        Usa selectinload para cargar las relaciones en una sola query
        adicional, evitando el problema N+1.
        
        Args:
            ticket_id: ID del ticket
            
        Returns:
            El ticket con comments y state_log cargados
            
        Raises:
            HTTPException: Si el ticket no existe
        """
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
        """Lista tickets con filtros opcionales y paginación.
        
        El valor -1 en asignado_a_id significa "sin asignar" (NULL).
        
        Args:
            page: Número de página (empieza en 1)
            size: Tamaño de página (máx 100)
            estado: Filtrar por estado (opcional)
            prioridad: Filtrar por prioridad (opcional)
            asignado_a_id: Filtrar por usuario asignado (-1 = sin asignar)
            
        Returns:
            Página con items y total
        """
        filters = []
        if estado is not None:
            filters.append(Ticket.estado == estado)
        if prioridad is not None:
            filters.append(Ticket.prioridad == prioridad)
        if asignado_a_id is not None:
            # -1 significa "sin asignar" (NULL)
            if asignado_a_id == -1:
                filters.append(Ticket.asignado_a_id.is_(None))
            else:
                filters.append(Ticket.asignado_a_id == asignado_a_id)

        # Contar total
        total_stmt = select(func.count()).select_from(Ticket)
        if filters:
            total_stmt = total_stmt.where(*filters)
        total = await self.session.scalar(total_stmt) or 0

        # Obtener página
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
        """Valida que un usuario exista.
        
        Args:
            user_id: ID del usuario (None = sin asignar, es válido)
            
        Raises:
            HTTPException: Si el usuario no existe
        """
        from fastapi import HTTPException, status

        if user_id is None:
            return
        if await self.session.get(User, user_id) is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El usuario asignado no existe",
            )

    async def create(self, payload: TicketCreate) -> Ticket:
        """Crea un nuevo ticket.
        
        Args:
            payload: Datos del ticket a crear
            
        Returns:
            El ticket creado
        """
        await self.validate_assignee(payload.asignado_a_id)
        ticket = Ticket(**payload.model_dump())
        self.session.add(ticket)
        await self.session.commit()
        await self.session.refresh(ticket)
        return ticket

    async def update(self, ticket_id: int, payload: TicketUpdate) -> Ticket:
        """Actualiza parcialmente un ticket.
        
        Solo actualiza los campos presentes en el payload.
        
        Args:
            ticket_id: ID del ticket
            payload: Campos a actualizar
            
        Returns:
            El ticket actualizado
        """
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
        """Transiciona un ticket a un nuevo estado.
        
        Valida que la transición sea válida según la máquina de estados.
        
        Args:
            ticket_id: ID del ticket
            nuevo_estado: Estado al que transicionar
            
        Returns:
            El ticket actualizado
            
        Raises:
            InvalidTransitionError: Si la transición no es válida
        """
        ticket = await self.get_or_404(ticket_id)
        # Lanza InvalidTransitionError si no es válida
        assert_transition(ticket.estado, nuevo_estado)
        ticket.estado = nuevo_estado
        await self.session.commit()
        await self.session.refresh(ticket)
        return ticket

    async def add_comment(self, ticket_id: int, autor: str, payload: CommentCreate) -> Comment:
        """Añade un comentario a un ticket.
        
        Args:
            ticket_id: ID del ticket
            autor: Email del autor del comentario
            payload: Contenido del comentario
            
        Returns:
            El comentario creado
        """
        ticket = await self.get_or_404(ticket_id)
        comment = Comment(ticket_id=ticket.id, autor=autor, cuerpo=payload.cuerpo)
        self.session.add(comment)
        await self.session.commit()
        await self.session.refresh(comment)
        return comment

    async def to_out(self, ticket: Ticket) -> TicketOut:
        """Convierte un modelo Ticket a schema TicketOut.
        
        Asegura que la relación "asignado" esté cargada para
        poder incluir el email en la respuesta.
        
        Args:
            ticket: Modelo Ticket
            
        Returns:
            Schema TicketOut
        """
        await self.session.refresh(ticket, attribute_names=["asignado"])
        return TicketOut.model_validate(ticket)
