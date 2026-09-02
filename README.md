# Deskly — Sistema de tickets de soporte

Prototipo full-stack de un sistema de tickets de soporte: API con **FastAPI**,
frontend con **Next.js 14**, base de datos **PostgreSQL**, **Redis** para eventos
en tiempo real, todo orquestado con **Docker Compose**.

El código está en inglés; la documentación, en español. El proyecto se construyó
siguiendo *Spec-Driven Development* (ver `docs/specs/`) y las decisiones técnicas
están justificadas en [`DECISIONES.md`](./DECISIONES.md).

---

## Arranque

Requisitos: Docker y Docker Compose.

```bash
git clone <tu-repo>
cd deskly-tickets
# Copiar las plantillas de variables de entorno (una por servicio):
cp api/.env.example api/.env      # backend + infraestructura
cp web/.env.example web/.env      # frontend
docker compose up --build
```

> Las variables están separadas por servicio: `api/.env` (backend, base de
> datos, JWT, webhook, seed) y `web/.env` (URLs del frontend). Ningún secreto
> se versiona; solo los `.env.example`.

### Dos formas de ejecución (desarrollo y producción)

La única diferencia entre desarrollo y producción es si se **siembran datos de
ejemplo** al arrancar. Se controla con la variable `DESKLY_SEED` en `api/.env`:

| Modo | `DESKLY_SEED` | Qué hace al arrancar |
|------|---------------|----------------------|
| **Desarrollo** | `true`  | Crea admin + usuarios y tickets de ejemplo (si la BD está vacía) |
| **Producción** | `false` | No siembra datos; arranca limpio |

```bash
# Desarrollo (con datos de ejemplo) — valor por defecto en api/.env.example
DESKLY_SEED=true   docker compose up --build

# Producción (sin datos de ejemplo)
DESKLY_SEED=false  docker compose up --build
```

También puedes fijar el valor directamente en `api/.env`. Como el seed es
"crear-si-no-existe" y la base de datos persiste en un volumen, para un arranque
de producción totalmente limpio empieza con `DESKLY_SEED=false` desde el inicio
(o resetea el volumen con `docker compose down -v`).

Esto levanta cuatro servicios:

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| `web`    | 3000   | Frontend Next.js |
| `api`    | 8000   | API FastAPI |
| `db`     | (interno) | PostgreSQL 16 |
| `redis`  | (interno) | Redis 7 (pub/sub de eventos) |

- Frontend: http://localhost:3000
- API (docs OpenAPI): http://localhost:8000/docs
- Al arrancar, el contenedor de la API aplica las migraciones
  (`alembic upgrade head`) y siembra datos de ejemplo.

### Credenciales del seed

Se crea un usuario administrador inicial (configurable en `api/.env`):

- **Email:** `admin@deskly.com`
- **Contraseña:** `admin123`

También se crea un agente de ejemplo (`agente@deskly.com` / `agente123`) y unos
tickets de muestra. Cambia estas credenciales en `api/.env` antes de cualquier uso real.

---

## Verificación rápida

Con el stack levantado:

```bash
# 1) Salud del API (verifica DB y Redis)
curl http://localhost:8000/health

# 2) Login (obtiene un token JWT)
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@deskly.com","password":"admin123"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 3) Listar tickets (requiere autenticación)
curl http://localhost:8000/api/tickets -H "Authorization: Bearer $TOKEN"

# 4) Sin token debe devolver 401
curl -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/tickets
```

### Tests del backend

Los tests usan SQLite en memoria (no necesitan Docker). Con un Python 3.12:

```bash
cd api
python -m venv .venv && source .venv/bin/activate   # o: uv venv --python 3.12
pip install -r requirements.txt
pytest
```

Cubren la máquina de estados (transiciones válidas e inválidas), el webhook
(firma válida/inválida, payload malformado, idempotencia) y la autenticación
(login, rutas protegidas, permisos de administrador).

---

## Cómo probar el webhook manualmente

El webhook verifica una firma **HMAC-SHA256** del cuerpo con el secreto
`WEBHOOK_SECRET` (definido en `api/.env`), enviada en el header `X-Signature`.

```bash
SECRET=change-me   # el valor de WEBHOOK_SECRET en tu api/.env
BODY='{"event_id":"inc-001","titulo":"Ticket externo","descripcion":"Creado vía webhook","prioridad":"alta"}'
SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | sed 's/^.* //')

# Firma válida -> 201 (crea el ticket sin asignar)
curl -i -X POST http://localhost:8000/api/webhooks/tickets \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIG" \
  -d "$BODY"

# Firma inválida -> 401
curl -i -X POST http://localhost:8000/api/webhooks/tickets \
  -H "Content-Type: application/json" \
  -H "X-Signature: firma-incorrecta" \
  -d "$BODY"
```

**Notas:**

- **`event_id`**: texto libre (hasta 120 caracteres) que identifica el evento en el
  sistema del proveedor. Deskly usa `event_id` para garantizar **idempotencia**:
  si se reenvía el mismo `event_id`, devuelve el ticket existente sin crear un duplicado.

- **Asignación**: Los tickets creados vía webhook **siempre llegan sin asignar**
  (asignado_a_id = NULL). No hay campo `asignado_a_id` en el payload. Un agente
  deberá asignarse manualmente desde la interfaz de Deskly después de la creación.

- Firma inválida o ausente → **401 Unauthorized**.
- Firma válida pero payload malformado → **422 Unprocessable Entity**.
- Reenviar el mismo `event_id` → devuelve el ticket creado antes (idempotencia).

---

## Elección de base de datos: PostgreSQL

Elegí **PostgreSQL** sobre MongoDB porque el dominio es **relacional**: un ticket
tiene comentarios y un usuario asignado, y me interesa la integridad referencial
(borrar un ticket borra sus comentarios). Además, la **idempotencia del webhook**
se resuelve de forma sencilla con una restricción `UNIQUE` sobre `event_id`,
delegando la garantía a la propia base de datos. El detalle está en
[`DECISIONES.md`](./DECISIONES.md).

### Índices justificados

- `ix_tickets_estado` — el listado de tickets filtra por estado (el filtro más frecuente).
- `ix_tickets_prioridad` — segundo filtro disponible.
- `ix_tickets_asignado_a_id` — para consultar tickets por usuario asignado.
- `UNIQUE (event_id)` en `webhook_events` — garantiza la idempotencia del webhook.

---

## Funcionalidad

**Backend**
- CRUD de tickets con paginación y filtros por estado/prioridad/asignado.
- Máquina de estados explícita (`abierto → en_progreso → resuelto → cerrado`, con
  reapertura desde `resuelto`). Una transición inválida devuelve **409** con un
  mensaje claro, no un 500.
- Comentarios por ticket.
- Webhook de ingesta con firma HMAC-SHA256 (401/422), idempotencia por `event_id`.
- WebSocket `/ws/tickets` con eventos tipados (`DomainEvent` enum), difundidos vía
  **Redis pub/sub** (escala a varias instancias).
- Autenticación **JWT** y usuarios con permiso `is_admin`.
- Health check extendido que verifica DB y Redis.
- Repository Pattern para lógica de negocio desacoplada.

**Frontend**
- Listado de tickets con tabla paginada, filtros y highlight visual en actualizaciones.
- Detalle `/tickets/[id]` **renderizado en servidor (SSR)** con hilo de
  comentarios, historial de cambios y edición inline.
- React Query para cache y sincronización automática.
- Zod + react-hook-form para validación de formularios.
- Toasts (sonner) para feedback de acciones.
- Error Boundary para manejo de errores por página.
- Constants centralizadas para labels y colores.
- DataTable abstracto reutilizable.
- Hook `useTicketStream` (WebSocket) con reconexión automática e indicador de conexión.

---

## Arquitectura

### Backend
- `app/repositories/` — Lógica de negocio desacoplada de los routers.
- `app/routers/` — Endpoints HTTP delgados.
- `app/models.py` — Modelos SQLAlchemy con relaciones y listeners.
- `app/enums.py` — Enumeraciones tipadas (`Estado`, `Prioridad`, `DomainEvent`).
- `app/state_machine.py` — Máquina de estados explícita.

### Frontend
- `lib/api.ts` — Cliente API tipado con soporte SSR.
- `lib/schemas.ts` — Schemas Zod para validación de formularios.
- `lib/constants.ts` — Labels y colores centralizados.
- `lib/types.ts` — Tipos TypeScript espejo del backend.
- `components/DataTable.tsx` — Tabla abstracta reutilizable.
- `components/QueryProvider.tsx` — Provider de React Query.

---

## CI/CD

Pipeline con GitHub Actions:
- **Backend:** lint (ruff) + migrations check (alembic check) + tests (pytest)
- **Frontend:** lint (next lint) + build (type-check + compile)

---

## Límites conocidos

- **Idempotencia del webhook**: el manejo de una colisión concurrente exacta del
  mismo `event_id` (dos peticiones simultáneas) confía en la restricción `UNIQUE`
  de la base de datos.
- **Vulnerabilidad transitiva de `postcss`**: aparece en node_modules de Next.js.
  Solucionarla obliga a subir a Next 16 (cambio mayor).
- **Escalado del WebSocket**: preparado con Redis pub/sub, pero sin configuración
  de múltiples réplicas ni balanceador.
- **Seed con timestamps escalonados**: los inserts usan SQLAlchemy Core para
  evitar disparar los listeners de `events.py`, que fijarían `creado_en = now()`.

---

## Estructura del repositorio

```
api/            # Backend FastAPI (app/, alembic/, tests/)
web/            # Frontend Next.js 14 (app/, components/, hooks/, lib/)
docs/specs/     # Especificaciones SDD (requisitos, diseño, tareas)
docker-compose.yml
.env.example
DECISIONES.md   # Bitácora de decisiones y uso de LLM
```

---

## Tiempo invertido

_Aproximadamente 2 jornadas de trabajo (dedicación parcial): especificaciones,
backend, frontend, autenticación, Docker y documentación._
