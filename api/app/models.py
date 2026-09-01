"""
MÓDULO: models.py - Modelos ORM de SQLAlchemy

Estos modelos definen las tablas de la base de datos y sus relaciones.

Concepto ORM (Object-Relational Mapping):
- Una clase Python = una tabla de la BD
- Un atributo de la clase = una columna
- Una instancia de la clase = una fila

Ventajas del ORM:
- Escribes Python, no SQL directo
- Cambios de BD se reflejan en el código Python
- Migraciones automáticas con Alembic
- Type-safety: el IDE autocomplete funciona

Tablas en esta aplicación:
1. users: Usuarios (agentes y administradores)
2. tickets: Tickets de soporte
3. comments: Comentarios en tickets
4. webhook_events: Eventos de webhook (para idempotencia)
5. state_log: Auditoría de cambios de estado
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
    """
    Modelo de usuario del sistema.
    
    Un usuario puede ser:
    - Un agente de soporte (is_admin=False): atiende tickets
    - Un administrador (is_admin=True): gestiona usuarios y configuración
    
    Relaciones:
    - Tickets asignados a este usuario (en la tabla Ticket como asignado_a_id)
    - StateLog con cambios que este usuario hizo
    
    Tabla: users
    """
    __tablename__ = "users"

    # COLUMNAS
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True  # No puede haber dos usuarios con el mismo email
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    nombre: Mapped[str] = mapped_column(
        String(120),
        nullable=False
    )
    apellidos: Mapped[str] = mapped_column(
        String(120),
        nullable=False
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),  # La BD asigna la fecha actual
        nullable=False
    )

    @property
    def nombre_completo(self) -> str:
        """
        Propiedad calculada: devuelve nombre + apellidos.
        
        Se calcula al acceder, no se guarda en la BD.
        
        Returns:
            "Juan García" si nombre="Juan" y apellidos="García"
        """
        return f"{self.nombre} {self.apellidos}"


class Ticket(Base):
    """
    Modelo de un ticket de soporte.
    
    Un ticket representa un problema reportado por un cliente.
    Puede pasar por varios estados (abierto → resuelto → cerrado)
    y tener múltiples comentarios.
    
    Relaciones:
    - asignado: Usuario al que está asignado (puede ser NULL)
    - comments: Comentarios del ticket (se eliminan en cascada)
    - state_log: Historial de cambios (se elimina en cascada)
    
    Tabla: tickets
    Índices:
    - Por estado: dashboard filtra mucho por estado
    - Por prioridad: dashboard filtra por prioridad
    - Por asignado_a_id: para consultas "tickets de usuario X"
    """
    __tablename__ = "tickets"

    # COLUMNAS
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    titulo: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )
    descripcion: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    prioridad: Mapped[Prioridad] = mapped_column(
        String(20),
        nullable=False,
        default=Prioridad.media
    )
    estado: Mapped[Estado] = mapped_column(
        String(20),
        nullable=False,
        default=Estado.abierto
    )
    asignado_a_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),  # Si se borra el usuario, poner NULL
        nullable=True,
        index=True  # Índice para búsquedas rápidas
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),  # Se actualiza automáticamente en UPDATE
        nullable=False
    )

    # RELACIONES (referencias a otros modelos)
    # Carga "joined": en la misma query, traer el usuario asignado
    asignado: Mapped["User | None"] = relationship("User", lazy="joined")

    # Comentarios del ticket
    # cascade="all, delete-orphan": si se borra el ticket, borrar sus comentarios
    # order_by: ordenar comentarios por fecha de creación
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="Comment.creado_en",
    )

    # Historial de cambios de estado
    state_log: Mapped[list["StateLog"]] = relationship(
        cascade="all, delete-orphan",
        order_by="StateLog.creado_en.asc()",
    )

    # ÍNDICES
    __table_args__ = (
        Index("ix_tickets_estado", "estado"),
        Index("ix_tickets_prioridad", "prioridad"),
    )

    @property
    def asignado_a(self) -> str | None:
        """
        Propiedad calculada: devuelve el email del usuario asignado.
        
        Se usa en schemas TicketOut para devolver el email en la API.
        
        Returns:
            Email del usuario si está asignado, None si no
        """
        return self.asignado.email if self.asignado else None


class Comment(Base):
    """
    Modelo de un comentario en un ticket.
    
    Los comentarios documentan la progreso del ticket: qué se hizo,
    qué se descubrió, etc.
    
    Relación:
    - ticket: El ticket al que pertenece (eliminación en cascada)
    
    Tabla: comments
    """
    __tablename__ = "comments"

    # COLUMNAS
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    ticket_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tickets.id", ondelete="CASCADE"),  # Si se borra el ticket, borrar comentarios
        nullable=False,
        index=True
    )
    autor: Mapped[str] = mapped_column(
        String(120),
        nullable=False
    )
    cuerpo: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # RELACIONES
    # back_populates: referencia inversa (Ticket.comments)
    ticket: Mapped["Ticket"] = relationship(back_populates="comments")


class WebhookEvent(Base):
    """
    Modelo de un evento de webhook procesado.
    
    Se usa SOLO para garantizar idempotencia: si el mismo event_id
    se recibe dos veces, el webhook devuelve el ticket anterior sin
    crear un duplicado.
    
    El mecanismo:
    1. El cliente envía event_id en el webhook
    2. Buscamos en webhook_events si existe
    3. Si existe: devolvemos el ticket anterior
    4. Si no existe: creamos ticket y guardamos evento aquí
    
    La restricción UNIQUE en event_id asegura que la BD no permita
    inserts duplicados (como medida de seguridad).
    
    Tabla: webhook_events
    """
    __tablename__ = "webhook_events"

    # COLUMNAS
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    event_id: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        unique=True  # Garantiza idempotencia a nivel de BD
    )
    ticket_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False
    )
    procesado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )


class StateLog(Base):
    """
    Modelo de auditoría: registro de cambios de estado de tickets.
    
    Cada vez que un ticket cambia de estado o se asigna a alguien,
    se crea una entrada aquí para tener un historial completo.
    
    Ejemplo:
    - Evento 1: "Ticket creado con estado abierto"
    - Evento 2: "Cambio de status: en_progreso"
    - Evento 3: "Asignado a: juan@example.com"
    - Evento 4: "Cambio de status: resuelto"
    
    Este historial se muestra al usuario en el detalle del ticket.
    
    Relación:
    - ticket: El ticket al que pertenece
    
    Tabla: state_log
    """
    __tablename__ = "state_log"

    # COLUMNAS
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    ticket_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    mensaje: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    usuario_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
