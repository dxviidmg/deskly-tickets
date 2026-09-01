"""
MÓDULO: repositories/ticket.py - Repository Pattern para Tickets

¿Qué es Repository Pattern?
Un repository es un "intermediario" entre los routers (HTTP) y la BD (SQL).
Beneficios:
- Lógica de acceso a BD centralizada (fácil de cambiar/testear)
- Routers delgados (solo llaman al repo)
- Reutilizable: varios routers pueden usar el mismo repo
- Testeable: se puede mocker el repo en tests

Ejemplo:
    Sin repository:
        @router.get("/tickets")
        async def list_tickets(session):
            result = await session.scalars(select(Ticket)...)
            return result
    
    Con repository:
        @router.get("/tickets")
        async def list_tickets(repo: TicketRepository):
            return await repo.list(...)

¿Qué hace TicketRepository?
- Centraliza todas las queries sobre tickets
- Encapsula lógica de filtros, paginación, etc.
- Valida datos antes de guardar
- Transforma modelos ORM a schemas
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.enums import Estado, Prioridad
from app.models import Comment, Ticket, User
from app.schemas import (
    CommentCreate,
    Page,
    TicketCreate,
    TicketDetail,
    TicketOut,
    TicketUpdate,
)
from app.state_machine import assert_transition


class TicketRepository:
    """
    Repository para operaciones sobre Tickets.
    
    Centraliza todas las interacciones con la BD para tickets.
    Los routers llamanmétodos de esta clase en lugar de escribir
    queries SQL directamente.
    
    Métodos principales:
    - get_or_404: Obtener ticket por ID
    - get_with_details: Obtener ticket con comentarios e historial
    - list_with_filters: Listar con filtros y paginación
    - create: Crear nuevo ticket
    - update: Actualizar parcialmente
    - transition: Cambiar estado (validando máquina de estados)
    - add_comment: Agregar comentario
    - to_out: Convertir modelo ORM a schema
    """

    def __init__(self, session: AsyncSession):
        """
        Inicializa el repository con una sesión de BD.
        
        Args:
            session (AsyncSession): Sesión asíncrona de SQLAlchemy
                                    (inyectada desde FastAPI)
        """
        self.session = session

    async def get_or_404(self, ticket_id: int) -> Ticket:
        """
        Obtiene un ticket por ID o lanza HTTPException(404).
        
        Método de utilidad usado por otros métodos del repo
        y también por los routers.
        
        Args:
            ticket_id (int): ID del ticket
            
        Returns:
            Ticket: El modelo ORM
            
        Raises:
            HTTPException(404): Si el ticket no existe
        """
        from fastapi import HTTPException, status

        ticket = await self.session.get(Ticket, ticket_id)
        if ticket is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket no encontrado"
            )
        return ticket

    async def get_with_details(self, ticket_id: int) -> TicketDetail:
        """
        Obtiene un ticket con TODAS sus relaciones cargadas.
        
        Cargas:
        - comments: Lista de comentarios del ticket
        - state_log: Historial de cambios de estado
        - asignado: Usuario asignado (si existe)
        
        Usa selectinload para evitar el problema N+1:
        Sin selectinload: 1 query para el ticket + N queries para comentarios
        Con selectinload: 1 query para el ticket + 1 query para comentarios
        
        Args:
            ticket_id (int): ID del ticket
            
        Returns:
            TicketDetail: Schema con ticket, comentarios e historial
            
        Raises:
            HTTPException(404): Si no existe
        """
        from fastapi import HTTPException, status

        # Query: traer ticket con comentarios e historial en misma transacción
        stmt = (
            select(Ticket)
            .where(Ticket.id == ticket_id)
            .options(
                selectinload(Ticket.comments),
                selectinload(Ticket.state_log)
            )
        )
        ticket = await self.session.scalar(stmt)
        
        if ticket is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket no encontrado"
            )
        
        # Convertir a schema (TicketDetail = TicketOut + comments + state_log)
        return TicketDetail.model_validate(ticket)

    async def list_with_filters(
        self,
        page: int = 1,
        size: int = 20,
        estado: Estado | None = None,
        prioridad: Prioridad | None = None,
        asignado_a_id: int | None = None,
    ) -> Page[TicketOut]:
        """
        Lista tickets con filtros opcionales y paginación.
        
        Filtros:
        - estado: Abierto, en_progreso, resuelto, etc.
        - prioridad: Baja, media, alta, urgente
        - asignado_a_id: Usuario asignado (o -1 para sin asignar)
        
        Paginación:
        - page: 1, 2, 3, ... (1-indexed)
        - size: 20 por defecto (máximo 100)
        
        Devuelve:
        - items: Lista de tickets en la página
        - total: Total de tickets (sin paginar)
        - page: Página actual
        - size: Tamaño de página
        
        Ejemplo de uso:
            result = await repo.list_with_filters(
                page=1,
                size=20,
                estado=Estado.abierto,
                prioridad=Prioridad.alta,
                asignado_a_id=5
            )
        
        Args:
            page (int): Número de página (>= 1)
            size (int): Items por página (>= 1, <= 100)
            estado (Estado | None): Filtrar por estado
            prioridad (Prioridad | None): Filtrar por prioridad
            asignado_a_id (int | None): Filtrar por usuario asignado
                                        -1 significa "sin asignar" (NULL)
            
        Returns:
            Page[TicketOut]: Página de tickets
        """
        # Construir lista de filtros
        filters = []
        
        if estado is not None:
            filters.append(Ticket.estado == estado)
        
        if prioridad is not None:
            filters.append(Ticket.prioridad == prioridad)
        
        if asignado_a_id is not None:
            # Caso especial: -1 significa "sin asignar" (NULL)
            if asignado_a_id == -1:
                filters.append(Ticket.asignado_a_id.is_(None))
            else:
                filters.append(Ticket.asignado_a_id == asignado_a_id)

        # ===== CONTAR TOTAL =====
        total_stmt = select(func.count()).select_from(Ticket)
        if filters:
            total_stmt = total_stmt.where(*filters)
        total = await self.session.scalar(total_stmt) or 0

        # ===== OBTENER PÁGINA =====
        stmt = (
            select(Ticket)
            .where(*filters)
            .order_by(Ticket.creado_en.desc())  # Más recientes primero
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.session.scalars(stmt)
        
        # Convertir modelos ORM a schemas
        items = [TicketOut.model_validate(t) for t in result.all()]
        
        return Page[TicketOut](
            items=items,
            total=total,
            page=page,
            size=size
        )

    async def validate_assignee(self, user_id: int | None) -> None:
        """
        Valida que un usuario exista en la BD.
        
        Se usa antes de asignar un ticket a alguien, para evitar
        referências a usuarios inexistentes.
        
        Args:
            user_id (int | None): ID del usuario (None = sin asignar, es válido)
            
        Raises:
            HTTPException(422): Si el usuario no existe
        """
        from fastapi import HTTPException, status

        if user_id is None:
            # Sin asignar es válido
            return
        
        if await self.session.get(User, user_id) is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El usuario asignado no existe",
            )

    async def create(self, payload: TicketCreate) -> Ticket:
        """
        Crea un nuevo ticket.
        
        Proceso:
        1. Validar que el usuario asignado existe (si se especifica)
        2. Crear modelo Ticket
        3. Guardar en BD (commit)
        4. Recargar el objeto (para obtener creado_en del servidor)
        
        Args:
            payload (TicketCreate): Datos del ticket
            
        Returns:
            Ticket: Modelo ORM creado
            
        Raises:
            HTTPException(422): Si el usuario asignado no existe
        """
        await self.validate_assignee(payload.asignado_a_id)
        
        # Desempacar payload a kwargs
        ticket = Ticket(**payload.model_dump())
        self.session.add(ticket)
        await self.session.commit()
        await self.session.refresh(ticket)
        return ticket

    async def update(self, ticket_id: int, payload: TicketUpdate) -> Ticket:
        """
        Actualiza parcialmente un ticket.
        
        Solo actualiza los campos que están presentes en payload.
        Campos omitidos conservan su valor anterior.
        
        Nota: NO se puede cambiar el estado aquí. Usar transition() para eso.
        
        Args:
            ticket_id (int): ID del ticket
            payload (TicketUpdate): Campos a actualizar (todos opcionales)
            
        Returns:
            Ticket: Modelo actualizado
            
        Raises:
            HTTPException(404): Si el ticket no existe
            HTTPException(422): Si el usuario asignado no existe
        """
        ticket = await self.get_or_404(ticket_id)
        
        # Extraer solo los campos que fueron establecidos (exclude_unset=True)
        data = payload.model_dump(exclude_unset=True)
        
        # Validar usuario asignado si se está cambiando
        if "asignado_a_id" in data:
            await self.validate_assignee(data["asignado_a_id"])
        
        # Actualizar campos
        for field, value in data.items():
            setattr(ticket, field, value)
        
        await self.session.commit()
        await self.session.refresh(ticket)
        return ticket

    async def transition(self, ticket_id: int, nuevo_estado: Estado) -> Ticket:
        """
        Transiciona un ticket a un nuevo estado.
        
        Valida la transición usando la máquina de estados:
        - assert_transition() lanza InvalidTransitionError si no es válida
        - FastAPI la convierte en HTTP 409
        
        Args:
            ticket_id (int): ID del ticket
            nuevo_estado (Estado): Estado al que transicionar
            
        Returns:
            Ticket: Modelo con nuevo estado
            
        Raises:
            HTTPException(404): Si no existe
            HTTPException(409): Si la transición no es válida
        """
        ticket = await self.get_or_404(ticket_id)
        
        # Validar que la transición es permitida
        # (lanza InvalidTransitionError si no)
        assert_transition(ticket.estado, nuevo_estado)
        
        # Actualizar estado
        ticket.estado = nuevo_estado
        await self.session.commit()
        await self.session.refresh(ticket)
        return ticket

    async def add_comment(
        self,
        ticket_id: int,
        autor: str,
        payload: CommentCreate
    ) -> Comment:
        """
        Añade un comentario a un ticket.
        
        Args:
            ticket_id (int): ID del ticket
            autor (str): Email del autor (del usuario autenticado)
            payload (CommentCreate): { cuerpo: str }
            
        Returns:
            Comment: Modelo del comentario creado
            
        Raises:
            HTTPException(404): Si el ticket no existe
        """
        # Validar que el ticket existe
        ticket = await self.get_or_404(ticket_id)
        
        # Crear comentario
        comment = Comment(
            ticket_id=ticket.id,
            autor=autor,
            cuerpo=payload.cuerpo
        )
        self.session.add(comment)
        await self.session.commit()
        await self.session.refresh(comment)
        return comment

    async def to_out(self, ticket: Ticket) -> TicketOut:
        """
        Convierte un modelo Ticket a schema TicketOut.
        
        Asegura que la relación "asignado" esté cargada
        para que la propiedad asignado_a (email) funcione.
        
        Args:
            ticket (Ticket): Modelo ORM
            
        Returns:
            TicketOut: Schema listo para devolver como JSON
        """
        # Recargar la relación "asignado" para asegurar que esté presente
        await self.session.refresh(ticket, attribute_names=["asignado"])
        return TicketOut.model_validate(ticket)
