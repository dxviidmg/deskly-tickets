"""Tests for authentication and user-management permissions."""
import pytest

from tests.conftest import _create_user


@pytest.mark.asyncio
async def test_login_success_returns_token(client):
    await _create_user(client.test_session, "a@test.com", "secret123", is_admin=False)
    resp = await client.post(
        "/api/auth/login", json={"email": "a@test.com", "password": "secret123"}
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client):
    await _create_user(client.test_session, "b@test.com", "secret123", is_admin=False)
    resp = await client.post(
        "/api/auth/login", json={"email": "b@test.com", "password": "wrong"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_tickets_require_authentication(client):
    # No Authorization header -> 401.
    resp = await client.get("/api/tickets")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_user_can_list_tickets(admin_client):
    resp = await admin_client.get("/api/tickets")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_admin_can_create_user(admin_client):
    resp = await admin_client.post(
        "/api/users",
        json={"email": "new@test.com", "password": "secret123", "is_admin": False},
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "new@test.com"


@pytest.mark.asyncio
async def test_non_admin_cannot_manage_users(client):
    # Create a non-admin user and log in.
    await _create_user(client.test_session, "plain@test.com", "secret123", is_admin=False)
    login = await client.post(
        "/api/auth/login",
        json={"email": "plain@test.com", "password": "secret123"},
    )
    token = login.json()["access_token"]
    resp = await client.get(
        "/api/users", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_ticket_assignee_must_exist(admin_client):
    resp = await admin_client.post(
        "/api/tickets",
        json={
            "titulo": "Test",
            "descripcion": "desc",
            "prioridad": "media",
            "asignado_a_id": 9999,
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_invalid_transition_returns_409_over_http(admin_client):
    # Create a ticket (starts as "abierto") and attempt an invalid transition.
    # This exercises the full HTTP path: the estado comes back from the DB as a
    # string, so this guards against the 500 regression.
    created = await admin_client.post(
        "/api/tickets",
        json={"titulo": "T", "descripcion": "d", "prioridad": "media"},
    )
    tid = created.json()["id"]
    resp = await admin_client.post(
        f"/api/tickets/{tid}/transicion", json={"nuevo_estado": "cerrado"}
    )
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["actual"] == "abierto"
    assert detail["solicitado"] == "cerrado"
