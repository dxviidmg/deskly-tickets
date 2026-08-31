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
cp .env.example .env
docker compose up --build
```

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

Se crea un usuario administrador inicial (configurable en `.env`):

- **Email:** `admin@deskly.com`
- **Contraseña:** `admin123`

También se crea un agente de ejemplo (`agente@deskly.com` / `agente123`) y unos
tickets de muestra. Cambia estas credenciales en `.env` antes de cualquier uso real.

---

## Verificación rápida

Con el stack levantado:

```bash
# 1) Salud del API
curl http://localhost:8000/health        # {"status":"ok"}

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
(firma válida/ inválida, payload malformado, idempotencia) y la autenticación
(login, rutas protegidas, permisos de administrador).

---

## Cómo probar el webhook manualmente

El webhook verifica una firma **HMAC-SHA256** del cuerpo con el secreto
`WEBHOOK_SECRET` (definido en `.env`), enviada en el header `X-Signature`.

```bash
SECRET=change-me   # el valor de WEBHOOK_SECRET en tu .env
BODY='{"event_id":"evt-1","titulo":"Ticket externo","descripcion":"Creado vía webhook","prioridad":"alta"}'
SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | sed 's/^.* //')

# Firma válida -> 201 (crea el ticket)
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

- Firma inválida o ausente → **401**.
- Firma válida pero payload malformado → **422**.
- Reenviar el mismo `event_id` no crea un ticket duplicado (idempotencia).

---

## Elección de base de datos: PostgreSQL

Elegí **PostgreSQL** sobre MongoDB porque el dominio es **relacional**: un ticket
tiene comentarios y un usuario asignado, y me interesa la integridad referencial
(borrar un ticket borra sus comentarios). Además, la **idempotencia del webhook**
se resuelve de forma sencilla con una restricción `UNIQUE` sobre `event_id`,
delegando la garantía a la propia base de datos. El detalle está en
[`DECISIONES.md`](./DECISIONES.md).

### Índices justificados

- `ix_tickets_estado` — el listado del dashboard filtra por estado (el filtro más
  frecuente).
- `ix_tickets_prioridad` — segundo filtro disponible.
- `ix_tickets_asignado_a_id` — para consultar tickets por usuario asignado.
- `UNIQUE (event_id)` en `webhook_events` — garantiza la idempotencia del webhook.

---

## Funcionalidad

**Backend**
- CRUD de tickets con paginación y filtros por estado/prioridad.
- Máquina de estados explícita (`abierto → en_progreso → resuelto → cerrado`, con
  reapertura desde `resuelto`). Una transición inválida devuelve **409** con un
  mensaje claro, no un 500.
- Comentarios por ticket.
- Webhook de ingesta con firma HMAC-SHA256 (401/422), idempotencia por `event_id`
  y protección contra *replay* por timestamp.
- WebSocket `/ws/tickets` con eventos `ticket.creado` / `ticket.actualizado` /
  `ticket.comentado`, difundidos vía **Redis pub/sub** (escala a varias instancias).
- Autenticación **JWT** y usuarios con permiso `is_admin`.

**Frontend**
- Dashboard con tabla paginada y filtro; estados de UI diferenciados (carga,
  vacío, error).
- Detalle `/tickets/[id]` **renderizado en servidor (SSR)** con hilo de
  comentarios y botones de transición.
- Hook `useTicketStream` (WebSocket) con limpieza en `useEffect`, reconexión
  automática e indicador visible de conexión.
- Login y gestión de usuarios (solo administradores).

---

## Qué dejé fuera (y por qué)

- **Idempotencia/replay del webhook como "producción real"**: implementados, pero
  el manejo de una colisión concurrente exacta del mismo `event_id` (dos
  peticiones simultáneas) confía en la restricción `UNIQUE`; no añadí manejo
  explícito del `IntegrityError` concurrente por simplicidad.
- **La autenticación es una ampliación**: el enunciado no pedía usuarios ni login.
  Los añadí (usuarios, JWT, permisos `is_admin`, `asignado_a` como referencia a un
  usuario) como valor añadido, priorizándolos **después** de tener funcionando el
  núcleo. La decisión y sus límites están en `DECISIONES.md`.
- **Vulnerabilidad transitiva de `postcss`**: aparece dentro del `node_modules`
  propio de Next.js (herramienta de *build*, no de ejecución). Solucionarla obliga
  a subir a Next 16 (cambio mayor); no lo hice para no arriesgar la estabilidad del
  App Router en esta entrega.
- **Escalado del WebSocket**: preparado con Redis pub/sub, pero no incluí
  configuración de múltiples réplicas ni balanceador; queda como paso siguiente.

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
