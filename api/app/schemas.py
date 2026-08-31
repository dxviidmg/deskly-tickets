"""Pydantic v2 schemas for request/response validation."""
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.enums import Estado, Prioridad

T = TypeVar("T")


# --- Tickets -------------------------------------------------------------

class TicketCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    descripcion: str = Field(min_length=1)
    prioridad: Prioridad = Prioridad.media
    # Id of the user the ticket is assigned to (optional).
    asignado_a_id: int | None = None


class TicketUpdate(BaseModel):
    """Partial update. All fields optional; estado is changed via /transicion."""

    titulo: str | None = Field(default=None, min_length=1, max_length=200)
    descripcion: str | None = Field(default=None, min_length=1)
    prioridad: Prioridad | None = None
    asignado_a_id: int | None = None


class TransitionIn(BaseModel):
    nuevo_estado: Estado


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    descripcion: str
    prioridad: Prioridad
    estado: Estado
    asignado_a_id: int | None
    asignado_a: str | None  # assigned user's email (read-only, from relationship)
    creado_en: datetime
    actualizado_en: datetime


# --- Comments ------------------------------------------------------------

class CommentCreate(BaseModel):
    cuerpo: str = Field(min_length=1)


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
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
    asignado_a_id: int | None = None


# --- Auth & Users --------------------------------------------------------

class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    is_admin: bool = False


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)
    is_admin: bool | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    is_admin: bool
    creado_en: datetime
