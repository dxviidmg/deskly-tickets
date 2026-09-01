"""
MÓDULO: routers/webhooks.py - Ingesta de webhooks con firma HMAC-SHA256

Endpoint para recibir tickets de sistemas externos (CRM, email, formularios).

¿Qué es un webhook?
Un webhook es una llamada HTTP que un sistema externo hace a nuestro servidor
para notificar de algo que ocurrió (ej: nuevo ticket, formulario enviado).

Seguridad del webhook:
1. El cliente externo firma el body con HMAC-SHA256 y el secreto compartido
2. Lo envía en header X-Signature: sha256=...
3. Nosotros verificamos que la firma es válida
4. Si es válida, procesamos; si no, devolvemos 401

Idempotencia:
El cliente puede reenviar el mismo webhook (por conexiones perdidas, reintentos, etc).
Usamos event_id para detectar duplicados: si ya existe, devolvemos el ticket anterior.

Orden de validación (importante):
1. Firma HMAC → 401 si falla
2. Timestamp (opcional, replay protection) → 401 si está muy viejo
3. Payload JSON → 422 si está malformado
4. Idempotencia → chequear event_id existente
"""

import hashlib
import hmac
import json
import time

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_session
from app.events import TICKET_CREATED
from app.models import Ticket, WebhookEvent
from app.schemas import TicketOut, WebhookTicketIn
from app.ws import manager

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


def _valid_signature(secret: str, raw_body: bytes, provided: str | None) -> bool:
    """
    Verifica que la firma HMAC-SHA256 es válida.
    
    Proceso:
    1. Calcular HMAC-SHA256 del body con el secreto
    2. Comparar con la firma provista (con timing-safe compare)
    
    El header X-Signature puede incluir prefijo "sha256=" (algunos proveedores lo incluyen).
    Lo removemos antes de comparar.
    
    Args:
        secret: Secreto compartido (de config)
        raw_body: Body del request sin procesar
        provided: Valor del header X-Signature
        
    Returns:
        True si la firma es válida, False si no o si no se proporcionó
    """
    if not provided:
        return False
    
    # Calcular HMAC esperada
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    
    # Remover prefijo "sha256=" si existe
    provided = provided.removeprefix("sha256=")
    
    # Comparación timing-safe (resiste timing attacks)
    return hmac.compare_digest(expected, provided)


@router.post("/tickets", status_code=status.HTTP_201_CREATED)
async def ingest_ticket(
    request: Request,
    x_signature: str | None = Header(default=None),
    x_timestamp: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    """
    Endpoint para ingestar tickets de sistemas externos vía webhook.
    
    POST /api/webhooks/tickets
    Headers:
        X-Signature: sha256=<firma_hmac>
        X-Timestamp: <timestamp_unix> (opcional, para replay protection)
    Body (JSON):
        {
            "event_id": "ext-001",
            "titulo": "Nuevo ticket",
            "descripcion": "Descripción...",
            "prioridad": "alta"
        }
    
    Validaciones en orden:
    1. Firma HMAC → 401 si no es válida
    2. Timestamp → 401 si es demasiado viejo
    3. Payload JSON → 422 si no es válido
    4. Idempotencia → devolver ticket anterior si event_id existe
    
    Returns:
        TicketOut: Ticket creado (o existente si idempotencia)
        
    Raises:
        401: Firma inválida o expirada
        422: Payload malformado
    """
    # Obtener el body sin procesar para validar firma
    raw_body = await request.body()

    # 1) VALIDAR FIRMA → 401 si falla
    if not _valid_signature(settings.webhook_secret, raw_body, x_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firma inválida"
        )

    # 2) VALIDAR TIMESTAMP (replay protection, bonus)
    if x_timestamp is not None:
        try:
            age = abs(time.time() - float(x_timestamp))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Timestamp inválido",
            )
        
        # Rechazar si el timestamp es muy viejo (configurable, por defecto 5 minutos)
        if age > settings.webhook_max_age_seconds:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Petición expirada (posible replay)",
            )

    # 3) VALIDAR PAYLOAD → 422 si es inválido
    try:
        data = WebhookTicketIn.model_validate_json(raw_body)
    except (ValidationError, json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Payload malformado",
        ) from exc

    # 4) IDEMPOTENCIA
    # Buscar si ya procesamos este event_id
    existing = await session.scalar(
        select(WebhookEvent).where(WebhookEvent.event_id == data.event_id)
    )
    if existing is not None:
        # Ya existe, devolver ticket anterior (idempotencia)
        ticket = await session.get(Ticket, existing.ticket_id)
        await session.refresh(ticket, attribute_names=["asignado"])
        return TicketOut.model_validate(ticket)

    # CREAR TICKET
    ticket = Ticket(
        titulo=data.titulo,
        descripcion=data.descripcion,
        prioridad=data.prioridad,
        # Los tickets de webhook siempre se crean SIN ASIGNAR
        # Un agente los asignará manualmente después
    )
    session.add(ticket)
    await session.flush()  # Obtener el ID del ticket
    
    # GUARDAR EVENTO WEBHOOK para idempotencia futura
    session.add(WebhookEvent(event_id=data.event_id, ticket_id=ticket.id))
    await session.commit()
    
    # Cargar relación asignado antes de devolver
    await session.refresh(ticket, attribute_names=["asignado"])

    # Convertir a schema y publicar evento WebSocket
    out = TicketOut.model_validate(ticket)
    await manager.broadcast(TICKET_CREATED, out)
    
    return out
