"""
MÓDULO: schemas.py - Estructuras de datos (request/response)

Este archivo define esquemas Pydantic para validación automática de datos:

VALIDACIÓN: Cuando FastAPI recibe un request JSON, lo valida contra estos schemas.
Si el JSON no coincide, FastAPI automáticamente devuelve error 422.

Ejemplo:
    POST /api/tickets con JSON:
        { "titulo": "Mi ticket" }  (falta descripción)
    FastAPI comprueba TicketCreate y ve que descripción es obligatoria,
    devuelve 422 con un mensaje de error claro.

SERIALIZACIÓN: Cuando devolvemos un modelo ORM como respuesta HTTP,
FastAPI usa estos schemas para convertirlo a JSON válido.

Los schemas están separados de los modelos ORM para tener control sobre:
- Qué campos devolver (ej: no devolver hashed_password)
- Qué campos aceptar en requests (ej: no aceptar is_admin del cliente)
- Transformaciones (ej: calcular nombre_completo desde nombre + apellidos)
"""

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.enums import Estado, Prioridad

T = TypeVar("T")


# ========== TICKETS: REQUEST (Input) ==========

class TicketCreate(BaseModel):
    """
    Schema para crear un nuevo ticket.
    
    Campos:
    - titulo: Asunto del ticket (1-200 caracteres)
    - descripcion: Detalles del problema (mínimo 1 carácter)
    - prioridad: Nivel de urgencia (opcional, por defecto "media")
    - asignado_a_id: ID del agente asignado (opcional, NULL = sin asignar)
    """
    titulo: str = Field(min_length=1, max_length=200)
    descripcion: str = Field(min_length=1)
    prioridad: Prioridad = Prioridad.media
    asignado_a_id: int | None = None


class TicketUpdate(BaseModel):
    """
    Schema para actualizar un ticket existente.
    
    IMPORTANTE: todos los campos son opcionales (None por defecto).
    Solo se actualiza lo que se envía. El estado se cambia con /transicion,
    no aquí.
    
    Ejemplo: PATCH /api/tickets/5
        { "titulo": "Título actualizado" }  <- solo actualiza titulo
    """
    titulo: str | None = Field(default=None, min_length=1, max_length=200)
    descripcion: str | None = Field(default=None, min_length=1)
    prioridad: Prioridad | None = None
    asignado_a_id: int | None = None


class TransitionIn(BaseModel):
    """
    Schema para cambiar el estado de un ticket.
    
    Ejemplo: POST /api/tickets/5/transicion
        { "nuevo_estado": "en_progreso" }
    """
    nuevo_estado: Estado


# ========== TICKETS: RESPONSE (Output) ==========

class TicketOut(BaseModel):
    """
    Schema para devolver un ticket en respuestas HTTP.
    
    ConfigDict(from_attributes=True) permite que FastAPI construya
    esta respuesta desde un modelo ORM Ticket directamente.
    
    Campos:
    - id: ID único del ticket
    - estado: Estado actual
    - asignado_a: Email del usuario asignado (calculado desde la relación)
    - creado_en / actualizado_en: Timestamps
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    descripcion: str
    prioridad: Prioridad
    estado: Estado
    asignado_a_id: int | None
    asignado_a: str | None  # email del usuario asignado (de la relación)
    creado_en: datetime
    actualizado_en: datetime


# ========== COMENTARIOS ==========

class CommentCreate(BaseModel):
    """Schema para crear un comentario en un ticket."""
    cuerpo: str = Field(min_length=1)


class CommentOut(BaseModel):
    """Schema para devolver un comentario."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    autor: str  # Email del autor
    cuerpo: str
    creado_en: datetime


# ========== TICKETS DETALLADO ==========

class TicketDetail(TicketOut):
    """
    Schema extendido de un ticket con comentarios e historial.
    
    Se devuelve cuando haces GET /api/tickets/5 (detalle completo),
    a diferencia de GET /api/tickets (lista, donde devuelves TicketOut).
    
    Incluye:
    - comments: Lista de comentarios del ticket
    - state_log: Historial de cambios de estado
    """
    comments: list[CommentOut] = []
    state_log: list["StateLogOut"] = []


# ========== PAGINACIÓN ==========

class Page(BaseModel, Generic[T]):
    """
    Schema genérico para paginar resultados.
    
    Se usa así: Page[TicketOut] = lista de tickets con info de paginación
    
    Ejemplo de respuesta:
        {
            "items": [ticket1, ticket2, ...],
            "total": 150,           # Total de items (no solo en esta página)
            "page": 1,              # Página actual
            "size": 20              # Items por página
        }
    """
    items: list[T]
    total: int
    page: int
    size: int


# ========== WEBHOOK ==========

class WebhookTicketIn(BaseModel):
    """
    Schema para aceptar peticiones del webhook de ingesta.
    
    Estos tickets llegan desde sistemas externos (CRM, email, etc.).
    
    Campos:
    - event_id: Identificador único en el sistema del proveedor
              Usado para garantizar idempotencia (no duplicar si se reenvía)
    - titulo, descripción, prioridad: Igual que TicketCreate
    - NO tiene asignado_a_id: los webhooks siempre crean tickets sin asignar
    """
    event_id: str = Field(min_length=1, max_length=120)
    titulo: str = Field(min_length=1, max_length=200)
    descripcion: str = Field(min_length=1)
    prioridad: Prioridad = Prioridad.media


# ========== AUTENTICACIÓN & USUARIOS ==========

class LoginIn(BaseModel):
    """Schema para login: email + contraseña."""
    email: EmailStr  # Validación de email automática
    password: str = Field(min_length=1)


class Token(BaseModel):
    """
    Schema para devolver un token JWT después de login exitoso.
    
    El cliente recibe:
        { "access_token": "eyJ0eXAi...", "token_type": "bearer" }
    
    Y debe enviar en requests posteriores:
        Authorization: Bearer eyJ0eXAi...
    """
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    """
    Schema para crear un usuario (admin-only).
    
    Campos:
    - email: Único en el sistema
    - password: Mínimo 6 caracteres (será hasheada)
    - nombre, apellidos: Para identificar el usuario
    - is_admin: Si puede gestionar otros usuarios
    """
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    nombre: str = Field(min_length=1, max_length=120)
    apellidos: str = Field(min_length=1, max_length=120)
    is_admin: bool = False


class UserUpdate(BaseModel):
    """
    Schema para actualizar un usuario (admin-only).
    
    Todos los campos son opcionales (actualización parcial).
    """
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    apellidos: str | None = Field(default=None, min_length=1, max_length=120)
    is_admin: bool | None = None


class UserOut(BaseModel):
    """
    Schema para devolver un usuario.
    
    NO incluye hashed_password (campo sensible, nunca se devuelve).
    Sí incluye nombre_completo (calculado en el modelo).
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    nombre: str
    apellidos: str
    nombre_completo: str  # Propiedad del modelo
    is_admin: bool
    creado_en: datetime


class UserOption(BaseModel):
    """
    Schema reducido de usuario para selects/dropdowns.
    
    Se usa en el frontend para llenar desplegables de usuarios
    (ej: "Asignar a:"). Solo devuelve id + email, sin datos sensibles.
    
    Ejemplo de respuesta:
        [
            { "id": 1, "email": "juan@company.com", "nombre_completo": "Juan García" },
            { "id": 2, "email": "maria@company.com", "nombre_completo": "María López" }
        ]
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    nombre_completo: str


class StateLogOut(BaseModel):
    """
    Schema para devolver una entrada del historial de cambios.
    
    Se usa en TicketDetail para mostrar el timeline de cambios
    (ej: "Cambio de status: en_progreso").
    
    Campos:
    - mensaje: Descripción del cambio
    - usuario_id: Quién hizo el cambio (puede ser NULL)
    - creado_en: Cuándo ocurrió
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    mensaje: str
    usuario_id: int | None
    creado_en: datetime
