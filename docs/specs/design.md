# Diseño — Deskly

Documento de diseño técnico. Traduce los requisitos a arquitectura, modelo de
datos, contratos de API y decisiones de implementación.

---

## 1. Arquitectura general

```
┌──────────────┐        REST / WS         ┌──────────────────┐
│  Next.js 14  │ ───────────────────────▶ │   FastAPI (api)  │
│   (web)      │ ◀─── WebSocket eventos ── │                  │
└──────────────┘                          │  ConnectionMgr   │
      │ SSR                                │  Máquina estados │
      ▼                                    │  Webhook HMAC    │
   Navegador                               └────────┬─────────┘
                                                    │ SQLAlchemy async
                                                    ▼
                                            ┌──────────────────┐
    Sistema externo ── webhook firmado ──▶  │   PostgreSQL     │
                                            └──────────────────┘
```

- **Backend**: FastAPI (async), SQLAlchemy 2.0 async, Alembic, Pydantic v2.
- **Frontend**: Next.js 14 App Router, TypeScript, Tailwind.
- **DB**: PostgreSQL 16.
- **Tiempo real**: Redis (pub/sub) para difundir eventos WebSocket entre
  instancias.
- **Orquestación**: Docker Compose (api + web + db + redis).

## 2. Decisión de base de datos: PostgreSQL

Se elige PostgreSQL sobre MongoDB por:

- El dominio es **relacional**: un ticket tiene muchos comentarios; interesa
  integridad referencial (FK con `ON DELETE CASCADE`).
- La **idempotencia del webhook** se implementa de forma sencilla y segura con
  una constraint `UNIQUE (event_id)`, delegando la garantía a la DB.
- Los **filtros y paginación** del listado se benefician de índices B-tree sobre
  `estado` y `prioridad`.
- Las transiciones de estado se benefician de transacciones ACID.

Alternativa descartada (MongoDB): aportaría esquema flexible que aquí no
necesitamos y complicaría el hilo de comentarios y la unicidad del `event_id`.

### Índices justificados

- `ix_tickets_estado` sobre `tickets.estado`: el listado principal filtra por
  estado; es el filtro más frecuente del dashboard.
- `ix_tickets_prioridad` sobre `tickets.prioridad`: segundo filtro disponible.
- `uq_webhook_event_id` (UNIQUE) sobre `webhook_events.event_id`: garantiza
  idempotencia del webhook.

## 3. Modelo de datos

### Tabla `tickets`

| Columna         | Tipo                    | Notas                              |
|-----------------|-------------------------|------------------------------------|
| id              | INTEGER (PK)            | autoincremental                    |
| titulo          | VARCHAR(200) NOT NULL   |                                    |
| descripcion     | TEXT NOT NULL           |                                    |
| prioridad       | VARCHAR(20)             | baja, media, alta, urgente (validado en app) |
| estado          | VARCHAR(20)             | abierto, en_progreso, resuelto, cerrado (validado en app) |
| asignado_a      | VARCHAR(120) NULL       | nombre/email del agente            |
| creado_en       | TIMESTAMPTZ NOT NULL    | default now()                      |
| actualizado_en  | TIMESTAMPTZ NOT NULL    | se refresca en cada update         |

### Tabla `comments`

| Columna     | Tipo                     | Notas                        |
|-------------|--------------------------|------------------------------|
| id          | INTEGER (PK)             | autoincremental              |
| ticket_id   | INTEGER FK → tickets.id  | ON DELETE CASCADE, indexado  |
| autor       | VARCHAR(120) NOT NULL    |                              |
| cuerpo      | TEXT NOT NULL            |                              |
| creado_en   | TIMESTAMPTZ NOT NULL     | default now()                |

### Tabla `webhook_events` (idempotencia)

| Columna       | Tipo                    | Notas                         |
|---------------|-------------------------|-------------------------------|
| id            | INTEGER (PK)            | autoincremental               |
| event_id      | VARCHAR(120) UNIQUE     | id del evento externo         |
| ticket_id     | INTEGER FK → tickets.id | |
| procesado_en  | TIMESTAMPTZ            | default now()                 |

## 4. Máquina de estados

Definida como un mapa explícito estado → conjunto de destinos permitidos:

```python
ALLOWED_TRANSITIONS = {
    Estado.abierto:     {Estado.en_progreso},
    Estado.en_progreso: {Estado.resuelto},
    Estado.resuelto:    {Estado.cerrado, Estado.abierto},  # cerrar o reabrir
    Estado.cerrado:     set(),
}
```

- Una función `can_transition(actual, destino) -> bool` centraliza la regla.
- Si la transición no es válida se lanza `InvalidTransitionError`, mapeada por un
  exception handler a **HTTP 409** con cuerpo:
  `{"detail": {"actual": ..., "solicitado": ..., "permitidas": [...]}}`.

## 5. Contratos de API

Base: `/api`. Errores de validación → `422` (Pydantic). No encontrado → `404`.

| Método | Ruta                              | Cuerpo                         | Éxito |
|--------|-----------------------------------|--------------------------------|-------|
| POST   | /tickets                          | TicketCreate                   | 201   |
| GET    | /tickets?page&size&estado&prioridad | —                            | 200   |
| GET    | /tickets/{id}                     | —                              | 200   |
| PATCH  | /tickets/{id}                     | TicketUpdate (parcial)         | 200   |
| POST   | /tickets/{id}/transicion          | {nuevo_estado}                 | 200   |
| POST   | /tickets/{id}/comentarios         | {autor, cuerpo}                | 201   |
| POST   | /webhooks/tickets                 | payload firmado (X-Signature)  | 201   |
| WS     | /ws/tickets                       | —                              | —     |
| GET    | /users/options?q&limit            | — (auth)                       | 200   |

### Asignación con autocompletado (detalle de ticket)

- `GET /api/users/options` está disponible para **cualquier usuario
  autenticado** (a diferencia del CRUD `/api/users`, que es solo-admin). Devuelve
  `{id, email, nombre_completo}` para poblar selects sin exponer datos sensibles.
- El modelo `User` tiene `nombre` y `apellidos` (obligatorios) y una propiedad
  `nombre_completo` = `"{nombre} {apellidos}"`.
- Parámetros: `q` filtra sin distinción de mayúsculas por **email, nombre y
  apellidos** (incluida la concatenación `nombre || ' ' || apellidos`, para que
  "victor hernandez" encuentre a Victor Hernandez); `limit` por defecto 5.
  En el frontend, un componente propio `UserAutocomplete` (Tailwind, sin MUI)
  muestra un buscador; la primera opción es "Asignarme a mí" (usuario actual).
  Al elegir, hace `PATCH /api/tickets/{id}` con `asignado_a_id` y refresca.

### Esquemas Pydantic (v2)

- `TicketCreate`: titulo, descripcion, prioridad, asignado_a?
- `TicketUpdate`: todos opcionales (titulo?, descripcion?, prioridad?, asignado_a?)
- `TicketOut`: todos los campos + id + timestamps
- `TransitionIn`: nuevo_estado (Estado)
- `CommentCreate`: autor, cuerpo
- `CommentOut`: id, autor, cuerpo, creado_en
- `Page[T]`: items, total, page, size
- `WebhookTicketIn`: event_id, titulo, descripcion, prioridad, asignado_a?

## 6. Webhook — verificación de firma

1. Se lee el **cuerpo crudo** (`await request.body()`).
2. Se calcula `hmac.new(secret, raw_body, sha256).hexdigest()`.
3. Se compara con el header `X-Signature` usando `hmac.compare_digest`.
4. Firma inválida/ausente → `401`. Cuerpo válido pero payload malformado → `422`
   (se valida con Pydantic después de verificar la firma).

Orden importante: **primero firma (401), luego forma (422)**.

## 7. WebSocket — ConnectionManager

- `ConnectionManager` mantiene una lista de `WebSocket` activos por proceso.
- `connect` acepta y registra; `disconnect` elimina del registro.
- `broadcast(tipo, datos)` publica el evento en un canal de Redis; un subscriptor
  de fondo en cada instancia relaya el mensaje a sus conexiones locales. Si un
  envío a un cliente falla, se marca esa conexión para eliminación (desconexión
  limpia, sin errores silenciosos).
- Los endpoints REST que mutan estado (crear/actualizar/transicionar/comentar)
  publican el evento correspondiente tras confirmar en DB.

Formato de evento:

```json
{ "tipo": "ticket.actualizado", "datos": { ...TicketOut } }
```

Escalado: los eventos viajan por Redis pub/sub (canal `deskly:events`), de modo
que funcionan con múltiples instancias/workers del backend. Si Redis no está
disponible (p. ej. en tests o arranque local sin broker), el manager difunde solo
a las conexiones locales del proceso (modo de respaldo tolerante a fallos).

## 8. Historial de cambios (StateLog)

Tabla `state_log` para registrar transiciones y asignaciones con un mensaje legible:

```sql
CREATE TABLE state_log (
  id SERIAL PRIMARY KEY,
  ticket_id INT NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
  mensaje TEXT NOT NULL,  -- "Cambio de status: abierto → en_progreso" o "Asignado a: user@example.com"
  usuario_id INT REFERENCES users(id),  -- quién hizo el cambio (puede ser NULL si no hay usuario)
  creado_en TIMESTAMP DEFAULT NOW(),
  INDEX ix_state_log_ticket_id (ticket_id),
  INDEX ix_state_log_creado_en (creado_en)
);
```

**Registro:** 
- Al transicionar, se inserta `mensaje = f"Cambio de status: {estado_anterior} → {estado_nuevo}"`.
- Al asignar, se inserta `mensaje = f"Asignado a: {usuario_nuevo.email}"` (si era sin asignar antes) o `"Asignado a: {usuario_nuevo.email}"` (así no guarda el anterior, pero es legible).
- El `usuario_id` es quién hizo el cambio (usuario autenticado).

El endpoint `GET /api/tickets/{id}` incluye `state_log` como array de objetos `{ id, mensaje, usuario_id, creado_en }`, ordenado por `creado_en DESC`.

## 9. Frontend

- `/` (dashboard): Server Component que hace fetch inicial paginado; filtro por
  estado vía query param. Estados de UI: carga (skeleton), vacío (mensaje +
  ilustración), error (mensaje + reintento).
- `/tickets/[id]`: Server Component (SSR) que hace fetch del ticket + comentarios.
  Botones de transición como Client Component que llaman al backend.
- `useTicketStream`: hook cliente que abre el WebSocket, actualiza estado local
  al recibir eventos, limpia la conexión en el cleanup de `useEffect`, y expone
  el estado de conexión para el indicador.

## 9. Estructura de carpetas

```
api/
  app/
    main.py            # app FastAPI, routers, exception handlers, lifespan
    config.py          # settings Pydantic
    db.py              # engine async, session
    models.py          # SQLAlchemy
    schemas.py         # Pydantic v2
    enums.py           # Estado, Prioridad
    state_machine.py   # transiciones + errores
    ws.py              # ConnectionManager + Redis pub/sub
    events.py          # constantes de tipos de evento
    bootstrap.py       # seed de datos de ejemplo
    routers/
      tickets.py
      webhooks.py
      websocket.py
  alembic/             # migraciones
  tests/
web/
  app/
    page.tsx           # dashboard
    tickets/[id]/page.tsx
  lib/api.ts           # cliente tipado
  hooks/useTicketStream.ts
  components/
docs/specs/
```
