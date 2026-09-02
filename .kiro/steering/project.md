# Proyecto — Deskly

Sistema de tickets de soporte full-stack. Código en inglés; documentación en español.

## Stack real

- **Backend:** FastAPI 0.115, SQLAlchemy 2.0 (async), Alembic, PostgreSQL (asyncpg),
  Redis (pub/sub), Pydantic + pydantic-settings, JWT (python-jose), passlib+bcrypt.
- **Frontend:** Next.js 14 (App Router), React 18, TypeScript 5, TanStack Query 5,
  react-hook-form + Zod, sonner (toasts), Tailwind.
- **Infra:** Docker Compose (servicios `db`, `redis`, `api`, `web`).

> No hay otras tecnologías. No asumir Redux, Celery, GraphQL, capa de services, etc.

## Arquitectura

- **Backend** (`api/app/`): `routers/` (HTTP delgado) → `repositories/` (lógica de
  negocio y acceso a datos) → `models.py` (SQLAlchemy). Config en `config.py`
  (Settings), máquina de estados en `state_machine.py`, WebSocket en `ws.py`,
  eventos de dominio en `enums.py` (`DomainEvent`). No existe capa `services/`.
- **Frontend** (`web/`): `app/` (App Router: páginas y layouts), `components/`,
  `hooks/`, `lib/` (`api.ts` cliente tipado, `schemas.ts` Zod, `types.ts`,
  `constants.ts`). Providers: `QueryProvider`, `AuthProvider`.

## Comunicación frontend ↔ backend

- REST bajo `/api/*`. El cliente vive en `lib/api.ts`.
- **Navegador** usa `NEXT_PUBLIC_API_URL`; **SSR** usa `API_INTERNAL_URL`
  (nombre de servicio Docker `api:8000`). Ver `web/.env.example`.
- Tiempo real vía WebSocket `/ws/tickets` (`hooks/useTicketStream.ts`), con
  fan-out por Redis pub/sub.
- Auth por JWT (Bearer). Rutas protegidas con dependencias FastAPI.

## Convenciones

- Código en inglés; comentarios/documentación en español.
- Variables de entorno por servicio: `api/.env` (backend/infra), `web/.env`
  (frontend). Ningún secreto ni URL hardcodeado en `.py`/`.ts`/`.tsx`.
- Config obligatoria sin defaults (fail-fast). Ver `backend.md`.
- Commits atómicos; decisiones relevantes en `DECISIONES.md`.

## Principios

- Cambios pequeños y enfocados; resolver solo lo pedido.
- La spec manda (ver `sdd.md`). Eficiencia de contexto (ver `efficiency.md`).
