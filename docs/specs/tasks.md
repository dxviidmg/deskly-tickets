# Plan de tareas — Deskly

Plan de implementación incremental. Cada tarea corresponde a un commit atómico
con mensaje descriptivo (en inglés). El orden prioriza el núcleo obligatorio
antes que los bonus.

Leyenda: `[ ]` pendiente · `[x]` hecho · *(bonus)* opcional.

---

## Fase 0 — Especificación (SDD)

- [x] `docs: add requirements spec`
- [x] `docs: add design spec`
- [x] `docs: add tasks plan`

## Fase 1 — Backend: cimientos

- [ ] `chore(api): scaffold FastAPI project with config and async db`
  - `config.py` (Settings Pydantic), `db.py` (engine/session async), `main.py`.
- [ ] `feat(api): add ticket, comment and webhook_event models`
  - `models.py` + enums de estado y prioridad.
- [ ] `chore(api): configure alembic and initial migration`

## Fase 2 — Backend: dominio

- [ ] `feat(api): add pydantic v2 schemas`
- [ ] `feat(api): add explicit ticket state machine`
  - `state_machine.py` + `InvalidTransitionError`.

## Fase 3 — Backend: API REST

- [ ] `feat(api): implement ticket CRUD with pagination and filter`
- [ ] `feat(api): implement state transition endpoint (409 on invalid)`
- [ ] `feat(api): implement comments endpoint`

## Fase 4 — Backend: webhook y tiempo real

- [ ] `feat(api): implement HMAC-signed ingestion webhook`
  - 401 firma inválida, 422 payload malformado.
  - *(bonus)* idempotencia por `event_id`, protección replay por timestamp.
- [ ] `feat(api): implement websocket connection manager and events`

## Fase 5 — Backend: tests

- [ ] `test(api): cover state machine valid and invalid transitions`
- [ ] `test(api): cover webhook valid and invalid signature`

## Fase 6 — Frontend

- [ ] `chore(web): scaffold next.js 14 app router with typed api client`
- [ ] `feat(web): dashboard with paginated table, filter and UI states`
- [ ] `feat(web): SSR ticket detail with comments and transition buttons`
- [ ] `feat(web): useTicketStream hook with connection indicator`

## Fase 7 — DevOps

- [ ] `chore: add dockerfiles, docker-compose and .env.example`
- [ ] `feat(api): add seed script with sample data`

## Fase 8 — Documentación y cierre

- [ ] `docs: add README with setup, db choice, webhook test and scope`
- [ ] `docs: add DECISIONES.md`
- [ ] Verificación final: `docker compose up --build` y tests en verde.

---

## Priorización (si el tiempo se acorta)

1. CRUD + máquina de estados + tests (correctitud, 30 %).
2. Webhook HMAC + tests (correctitud + infra).
3. WebSocket + frontend en vivo (frontend, 15 %).
4. SSR detalle + estados de UI.
5. Docker Compose funcional (requisito de arranque; sin esto no se evalúa).
6. Documentación (razonamiento, 15 %).
7. Bonus.

El arranque con Docker Compose y la documentación son innegociables: sin arranque
no se evalúa, y el razonamiento documentado pesa 15 %.
