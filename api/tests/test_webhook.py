"""Integration tests for the ingestion webhook signature verification."""
import json

import pytest

from tests.conftest import WEBHOOK_SECRET, sign


def _payload() -> bytes:
    return json.dumps(
        {
            "event_id": "evt-1",
            "titulo": "Ticket externo",
            "descripcion": "Creado vía webhook",
            "prioridad": "alta",
        }
    ).encode()


@pytest.mark.asyncio
async def test_webhook_valid_signature_creates_ticket(client):
    body = _payload()
    resp = await client.post(
        "/api/webhooks/tickets",
        content=body,
        headers={
            "X-Signature": sign(WEBHOOK_SECRET, body),
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["titulo"] == "Ticket externo"
    assert data["estado"] == "abierto"


@pytest.mark.asyncio
async def test_webhook_invalid_signature_is_rejected(client):
    body = _payload()
    resp = await client.post(
        "/api/webhooks/tickets",
        content=body,
        headers={
            "X-Signature": "deadbeef",
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_webhook_missing_signature_is_rejected(client):
    body = _payload()
    resp = await client.post(
        "/api/webhooks/tickets",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_webhook_malformed_payload_returns_422(client):
    body = b'{"titulo": "sin event_id"}'  # valid signature, invalid schema
    resp = await client.post(
        "/api/webhooks/tickets",
        content=body,
        headers={
            "X-Signature": sign(WEBHOOK_SECRET, body),
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_webhook_idempotent_same_event_id(client):
    body = _payload()
    headers = {
        "X-Signature": sign(WEBHOOK_SECRET, body),
        "Content-Type": "application/json",
    }
    first = await client.post("/api/webhooks/tickets", content=body, headers=headers)
    second = await client.post("/api/webhooks/tickets", content=body, headers=headers)
    assert first.status_code == 201
    # Same event_id must not create a duplicate; returns the existing ticket.
    assert second.json()["id"] == first.json()["id"]

    listing = await client.get("/api/tickets")
    assert listing.json()["total"] == 1
