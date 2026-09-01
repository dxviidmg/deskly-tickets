#!/usr/bin/env bash
###############################################################################
# ARCHIVO: dev-infra.sh
# PROPÓSITO: (Modo B) Levantar SOLO la infraestructura (PostgreSQL + Redis) en
#            Docker, para desarrollar con api y web corriendo en tu máquina.
#
# ¿Por qué solo db y redis?
# En modo desarrollo quieres editar el backend (Python) y el frontend (Next.js)
# con recarga en vivo, ejecutándolos en tu terminal. Pero Postgres y Redis es
# más cómodo tenerlos en Docker. Este script levanta solo esos dos y expone sus
# puertos al host (ver docker-compose.override.yml):
#   - PostgreSQL -> localhost:5432
#   - Redis      -> localhost:6379
#
# USO:
#   ./dev-infra.sh          # arranca db + redis en segundo plano
#   ./dev-infra.sh down     # detiene db + redis
###############################################################################

set -euo pipefail

# Si el primer argumento es "down", detener la infraestructura y salir.
if [[ "${1:-}" == "down" ]]; then
  echo "Deteniendo db y redis..."
  docker compose stop db redis
  exit 0
fi

echo "Levantando db y redis en Docker (segundo plano)..."
# -d: modo detached (segundo plano). Solo db y redis, no api ni web.
docker compose up -d db redis

echo "Listo. PostgreSQL en localhost:5432, Redis en localhost:6379."
echo "Ahora arranca el backend con ./dev-api.sh y el frontend con ./dev-web.sh"
