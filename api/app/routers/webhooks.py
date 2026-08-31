"""Ingestion webhook with HMAC-SHA256 signature verification.

Verification order matters: the signature is checked first (401 on failure)
and only then is the payload validated (422 on malformed body).
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
    if not provided:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    # Allow an optional "sha256=" prefix used by many webhook providers.
    provided = provided.removeprefix("sha256=")
    return hmac.compare_digest(expected, provided)


@router.post("/tickets", status_code=status.HTTP_201_CREATED)
async def ingest_ticket(
    request: Request,
    x_signature: str | None = Header(default=None),
    x_timestamp: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    raw_body = await request.body()

    # 1) Signature first -> 401 on failure.
    if not _valid_signature(settings.webhook_secret, raw_body, x_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Firma inválida"
        )

    # 2) Replay protection (bonus): reject stale timestamps if provided.
    if x_timestamp is not None:
        try:
            age = abs(time.time() - float(x_timestamp))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Timestamp inválido",
            )
        if age > settings.webhook_max_age_seconds:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Petición expirada (posible replay)",
            )

    # 3) Payload validation -> 422 on malformed body.
    try:
        data = WebhookTicketIn.model_validate_json(raw_body)
    except (ValidationError, json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Payload malformado",
        ) from exc

    # 4) Idempotency (bonus): a known event_id returns the existing ticket.
    existing = await session.scalar(
        select(WebhookEvent).where(WebhookEvent.event_id == data.event_id)
    )
    if existing is not None:
        ticket = await session.get(Ticket, existing.ticket_id)
        await session.refresh(ticket, attribute_names=["asignado"])
        return TicketOut.model_validate(ticket)

    ticket = Ticket(
        titulo=data.titulo,
        descripcion=data.descripcion,
        prioridad=data.prioridad,
        asignado_a_id=data.asignado_a_id,
    )
    session.add(ticket)
    await session.flush()
    session.add(WebhookEvent(event_id=data.event_id, ticket_id=ticket.id))
    await session.commit()
    await session.refresh(ticket, attribute_names=["asignado"])

    out = TicketOut.model_validate(ticket)
    await manager.broadcast(TICKET_CREATED, out)
    return out
