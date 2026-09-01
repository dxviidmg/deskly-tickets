#!/usr/bin/env bash
################################################################################
# ARCHIVO: api/entrypoint.sh
# PROPÓSITO: Script de entrada para el contenedor FastAPI
#
# Responsabilidades:
# 1. Esperar a que PostgreSQL esté listo (healthcheck)
# 2. Aplicar migraciones de BD (Alembic)
# 3. Iniciar el servidor uvicorn
#
# ¿Por qué es necesario?
# Docker inicia el contenedor incluso si la BD aún no está lista.
# Dependemos de BD desde el minuto 1 (aplicar migraciones, conectar).
# Este script "espera" inteligentemente y evita fallos.
#
# Ejecución:
# - Dockerfile lo llama: ENTRYPOINT ["bash", "./entrypoint.sh"]
# - El contenedor arranca y ejecuta este script
################################################################################

# Exit on error: si algo falla, el script se detiene (no continúa ciegamente)
# -u: error si usa variable indefinida
# -o pipefail: error si algún comando en un pipe falla
set -euo pipefail

# ========== PASO 1: APLICAR MIGRACIONES ==========
echo "Applying database migrations (alembic upgrade head)..."

# Reintentar hasta 10 veces en caso de que la BD aún no esté lista
# (El healthcheck en docker-compose.yml esperará, pero podría haber
#  timeout o la BD podría estar iniciando aún)
for attempt in 1 2 3 4 5 6 7 8 9 10; do
  # Intentar aplicar migraciones
  if alembic upgrade head; then
    # Éxito, salir del loop
    echo "Migrations applied."
    break
  fi
  
  # Si falla, esperar 2s y reintentar
  echo "Database not ready yet (attempt ${attempt}); retrying in 2s..."
  sleep 2
done

# ========== PASO 2: ARRANCAR SERVIDOR ==========
echo "Starting uvicorn..."

# exec: reemplaza el proceso actual con uvicorn
# (hace que uvicorn sea PID 1, reciba signals de Docker, etc.)
# --host 0.0.0.0: escuchar en todas las interfaces (no solo localhost)
# --port 8000: puerto estándar
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
