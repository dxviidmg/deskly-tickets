# Backend (FastAPI)

Ubicación: `api/app/`. Stack real: FastAPI, Pydantic, SQLAlchemy 2.0 (async),
Alembic, PostgreSQL (asyncpg), Redis.

## Estructura y responsabilidades

- **`routers/`**: endpoints HTTP delgados. Sin lógica de negocio; delegan en
  repositories. Validan entrada/salida con schemas Pydantic.
- **`repositories/`**: lógica de negocio y acceso a datos (SQLAlchemy). Aquí van
  las reglas, no en los routers. **No existe capa `services/`; no crearla salvo
  que una spec lo pida.**
- **`models.py`**: modelos SQLAlchemy y relaciones.
- **`schemas.py`**: modelos Pydantic (entrada/salida). Mantener separados de los
  modelos ORM.
- **`config.py`**: `Settings` (pydantic-settings). Todos los campos son
  **obligatorios, sin default** (fail-fast). Ningún secreto/URL hardcodeado.
- **`state_machine.py`**: transiciones de estado explícitas; transición inválida
  → 409 (no 500).
- **`enums.py`**, **`ws.py`** (WebSocket + Redis), **`events.py`** (listeners).

## Async vs sync

- El acceso a BD y los endpoints son **async** (SQLAlchemy async + asyncpg).
  Usar `async def`, `await session.execute/scalar/commit`.
- Mantener el código sin operaciones bloqueantes dentro de handlers async.
  Trabajo puro/CPU o utilidades sin I/O pueden ser funciones sync normales.

## Migraciones (Alembic)

- Todo cambio de esquema requiere una migración Alembic.
- La URL de BD la provee `Settings` (no está en `alembic.ini`).

## Dependency Injection

- Usar `Depends(...)` para sesión de BD, settings, usuario actual y permisos
  (`get_session`, `get_settings`, `get_current_user`, `require_admin` en `deps.py`).
