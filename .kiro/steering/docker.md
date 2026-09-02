# Docker (uso mínimo)

Servicios: `db`, `redis`, `api`, `web` en `docker-compose.yml`.

## Cuándo NO usar Docker

- **No** hacer `docker compose build` para cambios normales de código. El backend
  (uvicorn `--reload`) y el frontend (`next dev`) tienen hot reload.
- **No** hacer `docker compose down` innecesariamente (perder el estado no aporta).
- No ejecutar comandos Docker si la tarea no lo requiere.

## Cuándo SÍ reconstruir

- Solo cuando cambien: **Dockerfiles**, **dependencias** (`requirements.txt`,
  `package.json`) o **configuración de build** (build args, etc.).
- Reconstruir/reiniciar únicamente el **servicio afectado**
  (p. ej. `docker compose up -d --build api`), no todo el stack.

## Logs

- Nunca cargar logs completos si no hace falta. Usar `--tail` (p. ej.
  `docker compose logs --tail 50 api`) y filtrar.

## Recordatorio

- El seed dev/prod se controla con `DESKLY_SEED` en `api/.env`
  (`true` desarrollo / `false` producción). No requiere archivos de compose extra.
