#!/usr/bin/env bash
###############################################################################
# ARCHIVO: dev-api.sh
# PROPÓSITO: (Modo B) Arrancar el backend FastAPI en LOCAL con recarga en vivo
#            (hot reload), conectándose a la db y Redis que corren en Docker.
#
# ¿Qué hace distinto al contenedor?
# El contenedor "api" se conecta al host "db". Pero cuando uvicorn corre en tu
# máquina, la db está en "localhost:5432". Por eso cargamos api/.env.local, que
# define DATABASE_URL/REDIS_URL apuntando a localhost, ANTES de arrancar uvicorn.
# Las variables de entorno tienen prioridad sobre el .env compartido.
#
# REQUISITOS:
#   - Haber levantado la infraestructura: ./dev-infra.sh
#   - Tener el venv en api/.venv (gestionado con uv/pip)
#
# USO:
#   ./dev-api.sh
###############################################################################

set -euo pipefail

# Movernos al directorio del backend (donde vive el paquete app/ y el venv).
cd "$(dirname "$0")/api"

# Cargar las variables del modo local (host = localhost).
# 'set -a' hace que toda variable asignada se exporte al entorno, para que
# uvicorn (y pydantic) las vean. 'set +a' lo desactiva después.
if [[ -f .env.local ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env.local
  set +a
else
  echo "ADVERTENCIA: no existe api/.env.local; se usarán los defaults (host 'db')."
fi

# Elegir intérprete: preferimos el uvicorn del venv del proyecto si existe.
if [[ -x .venv/bin/uvicorn ]]; then
  UVICORN=.venv/bin/uvicorn
else
  UVICORN=uvicorn
fi

echo "Backend local en http://localhost:8000 (DATABASE_URL=${DATABASE_URL:-<default db>})"
# --reload: recarga automática al cambiar el código (hot reload).
exec "$UVICORN" app.main:app --reload --host 0.0.0.0 --port 8000
