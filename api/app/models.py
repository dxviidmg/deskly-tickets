"""Modelos ORM de SQLAlchemy para la base de datos.

Define las tablas principales del sistema:
- User: Usuarios del sistema (agentes y administradores)
- Ticket: Tickets de soporte
- Comment: Comentarios en los tickets
- WebhookEvent: Eventos de webhook procesados (para idempotencia)
- StateLog: Registro de auditoría de cambios de estado
"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.enums import Estado, Prioridad


class User(Base):
    """Usuario del sistema (agente o administrador).
    
    Un usuario puede ser asignado a tickets y puede tener permisos de
    administrador (is_admin=True) para gestionar otros usuarios.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(120), nullable=False)
    # Si el usuario puede gestionar (CRUD) a otros usuarios
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    @property
    def nombre_completo(self) -> str:
        """Devuelve el nombre completo del usuario (nombre + apellidos)."""
        return f"{self.nombre} {self.apellidos}"


class Ticket(Base):
    """Ticket de soporte.
    
    Un ticket puede estar asignado a un usuario (agente) y tiene un ciclo
    de vida definido por la máquina de estados. Puede tener comentarios
    y un historial de cambios de estado.
    """
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    prioridad: Mapped[Prioridad] = mapped_column(
        String(20), nullable=False, default=Prioridad.media
    )
    estado: Mapped[Estado] = mapped_column(
        String(20), nullable=False, default=Estado.abierto
    )
    # El agente (usuario) al que está asignado el ticket. NULL = sin asignar
    asignado_a_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relación con el usuario asignado (carga eagerly con "joined")
    asignado: Mapped["User | None"] = relationship("User", lazy="joined")

    # Comentarios del ticket (se borran en cascada si se borra el ticket)
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="Comment.creado_en",
    )

    # Historial de cambios de estado (se borran en cascada)
    state_log: Mapped[list["StateLog"]] = relationship(
        cascade="all, delete-orphan",
        order_by="StateLog.creado_en.asc()",
    )

    __table_args__ = (
        # Índices para los filtros más comunes del dashboard
        Index("ix_tickets_estado", "estado"),
        Index("ix_tickets_prioridad", "prioridad"),
    )

    @property
    def asignado_a(self) -> str | None:
        """Devuelve el email del usuario asignado (para respuestas API)."""
        return self.asignado.email if self.asignado else None


class Comment(Base):
    """Comentario en un ticket.
    
    Los comentarios se muestran en el detalle del ticket y ayudan
    a documentar el progreso del mismo.
    """
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    autor: Mapped[str] = mapped_column(String(120), nullable=False)
    cuerpo: Mapped[str] = mapped_column(Text, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relación inversa con el ticket
    ticket: Mapped["Ticket"] = relationship(back_populates="comments")


class WebhookEvent(Base):
    """Evento de webhook procesado.
    
    Se usa para garantizar idempotencia: si se recibe el mismo event_id
    dos veces, solo se crea un ticket. La restricción UNIQUE en event_id
    lo impide a nivel de base de datos.
    """

    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(
        String(120), nullable=False, unique=True
    )
    ticket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE")
    )
    procesado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class StateLog(Base):
    """Registro de auditoría de cambios de estado y asignación.
    
    Cada vez que un ticket cambia de estado o de asignado, se registra
    aquí para tener un historial completo del ciclo de vida del ticket.
    """

    __tablename__ = "state_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    # Usuario que realizó el cambio (puede ser NULL si el listener no tiene acceso)
    usuario_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
