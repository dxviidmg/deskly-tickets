"""Pydantic v2 schemas for request/response validation."""
import uuid
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.enums import Estado, Prioridad

T = TypeVar("T")


# --- Tickets -------------------------------------------------------------

class TicketCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    descripcion: str = Field(min_length=1)
    prioridad: Prioridad = Prioridad.media
    asignado_a: str | None = Field(default=None, max_length=120)


class TicketUpdate(BaseModel):
    """Partial update. All fields optional; estado is changed via /transicion."""

    titulo: str | None = Field(default=None, min_length=1, max_length=200)
    descripcion: str | None = Field(default=None, min_length=1)
    prioridad: Prioridad | None = None
    asignado_a: str | None = Field(default=None, max_length=120)


class TransitionIn(BaseModel):
    nuevo_estado: Estado


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    titulo: str
    descripcion: str
    prioridad: Prioridad
    estado: Estado
    asignado_a: str | None
    creado_en: datetime
    actualizado_en: datetime


# --- Comments ------------------------------------------------------------

class CommentCreate(BaseModel):
    autor: str = Field(min_length=1, max_length=120)
    cuerpo: str = Field(min_length=1)


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_id: uuid.UUID
    autor: str
    cuerpo: str
    creado_en: datetime


class TicketDetail(TicketOut):
    comments: list[CommentOut] = []


# --- Pagination ----------------------------------------------------------

class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int


# --- Webhook -------------------------------------------------------------

class WebhookTicketIn(BaseModel):
    """Payload accepted by the ingestion webhook."""

    event_id: str = Field(min_length=1, max_length=120)
    titulo: str = Field(min_length=1, max_length=200)
    descripcion: str = Field(min_length=1)
    prioridad: Prioridad = Prioridad.media
    asignado_a: str | None = Field(default=None, max_length=120)
